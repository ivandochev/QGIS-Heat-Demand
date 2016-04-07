import math 
import timeit

tic=timeit.default_timer() # Timer begins:)

#Initialize Climate Data Dictionary
#Month[Days, AverageTemp, SolarNorth, SolarEast, SolarWest, SolarSouth, Horizontal]
Climate_data = [
    [
        31.0,0.5,22.9,40.4,40.4,72.7,50.1 # Jan
        ],
    [
        28.0,0.9,34.8,59.2,59.2,95.9,81.2 # Feb
        ],
    [
        31.0,4,47.7,68.4,68.4,87.5,109.0 # Mar
        ],
#   [
#        30.0,9.7,63.6,85.5,85.5,83.7,149.7 # April
#        ],
#    [
#        31.0,14.9,77.7,108.3,108.3,90.5,194.1 # May
#        ],
#    [
#        30.0,18.4,84.3,122,122,97.4,218.0 # June
#        ],
#    [
#        31.0,21,83.7,126.4,126.4,104.9,226.5 # July
#        ],
#    [
#        31.0,20.7,75.9,126.2,126.2,126.5,219.7 # Aug
#        ],
#    [
#        30.0,15.8,60.7,104.5,104.5,133.7,166.5 # Sep
#        ],
    [
        31.0,11.6,40.9,68.0,68.0,104.3,97.2 # Oct
        ],
    [
        30.0,6.3,26.1,45.8,45.8,80.6,58.3 # Nov
        ],
    [
        31.0,0.7,20.2,36.6,36.6,67.8,43.9 # Dec
        ]
]

#Field map initialization, change here for specifics of the shapefile
OBJECTID = 'OBJECTID'
Height = 'HEIGHT'
Floors = 'Floors'
Area = 'BuildArea'
Perimeter = 'BuildPerim'
Temperature = 'InsideTemp'
WallU = 'Walls'
WindowU = 'Windows'
RoofU = 'Roofs'
BaseU = 'Base'
EnEfWallsU = 'Walls_Reno'
EnEfWindowsU = 'Windows_Re'
EnEfRoofU = 'Roof_Renov' # Not used in algorithm yet
EnEfBaseU = 'Base_Renov' #Not used in algorithm yet
WinWallRatio = 'WinWallPer'
Inhabitants = 'Inhabitant'
PerIns = 'PerIns'
PerEnEfWin = 'PerEnEfWin'
RoofType = 'RoofType'
TotalAnnualHeatDemand = 'KWhAnnum'
TotalAnnualHeatDemandperSqMeter = 'KWhMetAnnu'
AirChangeRate = 'AirChR' #Add this to city wide script !!!!!!!!!!
InternalGainsPerSqMeter = 'IntGains' #Add this to city wide script !!!!!!!!!!
HeatedVolumeCoef = 'HtVolCoef' # Same here
SolarGainsFactor = 0.6*(1-0.3)*0.9*0.7 #=external_Shading*(1-Window Frame Area)*Non_Perpendicular*Solar Energy Transmittance - see tabula_calculator

#Prepare Formulas and Functions
def midpoint(pt1, pt2):
    x = (pt1.x()+pt2.x())/2
    y = (pt1.y()+pt2.y())/2
    return QgsPoint(x,y)

def Qhm(Qlm,Qgm,nm): #Equation 1
    Qhm = Qlm-Qgm*nm
    return Qhm

def Qlm(Hm,Temp,OutTemp,Days): #Equation2
    Qlm = 0.024*Hm*(Temp-OutTemp)*Days
    return Qlm

def Qgm(Solar,InternalGains,Days): #Equation3
    Qgm = 0.024*(Solar+InternalGains)*Days
    return Qgm

def Ht(UValue,Area): #Equation4 Hu and Htb are out, Htb shoud be added later for the whole building, Hu is not considered, as if all to outer space
    Ht = UValue*Area
    return Ht

def Hu(Area,U,InternalTemp,OutsideTemp,TempInUnheatedSpace): #Equation 5
    Fxi = (InternalTemp-TempInUnheatedSpace)/(InternalTemp-OutsideTemp)
    Hu = Area*U*Fxi
    return Hu

def HtbSimple(WholeSurface): #Equation6
    Utb = 0.1
    Htb = Utb*WholeSurface
    return Htb

def Hv(Volume,AirChangeRate,HeatVolumeCoeff): #Equation7
    Hv = AirChangeRate*HeatVolumeCoeff*Volume*0.34 # Change here, (AirChangeRate,0.8coefficient,Volume,HeatCapacityAir)
    return Hv

def SG(SolarRad,Surface,Factor): # Equation8 SG = Solar Gains = Fsm 
    SG = SolarRad*Surface*Factor
    return SG

def IG(Floors,FloorArea,InternalGainsCoeff): #Equation9_ A more precise Formula could be used!
    IG = InternalGainsCoeff*Floors*FloorArea
    return IG

def UtilFactor(Qgm,Qlm,Ht,Hv,Volume):#Equation10_
    a = 1+50*Volume/(Ht+Hv)/16
    y = Qgm/Qlm
    if y == 1:
        n = a/(a+1)
    else:
        n = (1-y**a)/(1-y**(a+1))
    return n
    
    
#Then initiailize mapCanvas and Layer:
canvas = qgis.utils.iface.mapCanvas()
layer = canvas.currentLayer()

layer.startEditing()
#This is a dictionary with all features, the f.id() produces
#numbers (in the case of TestBuild) from 0 to 39, it is then
#easier to lookup Features. NB. in order to view a feature geometry
#the .geometry() function has to be used, so if i print feature_dict[1]
#this means key 1 of feature_dict and will give me sth like
#<qgis._core.QgsFeature object at 0x0000000019B2C840>
#the if I want the geometry I have to use print feature_dict[1].geometry().asPolygon()
#so when I do for loops in the features I have to bare in mind that
#the dict has the features and not the geometries (well not exclusively)
#that is why later the geom variable is defined as 
#for f in feature_dict.values():
#    geom =f.geometry()
#Then I operate will the geometries (have to add asPolygon/asPolyline/asPoint)
#Get all Features into a Dict:
feature_dict = {f.id(): f for f in layer.selectedFeatures()}  #NB!!!! I have it to calculate only the selected Features!!!
#The the SpatialIndex is used to reference the features(not sure
#exactly how it works yet)
index = QgsSpatialIndex()
for f in feature_dict.values():
    index.insertFeature(f)
##Then come the features that intersect (are potential neighbours)
##here I have to modify the script by Ujaval Gandhi at
#http://www.qgistutorials.com/en/docs/find_neighbor_polygons.html
#to make it test if walls touch other buildings (kalkanni steni)
#Still I will first find all features that are within the boundingBox
#of the feature and then take out the feauter itself from the list (since it is also there)



for f in feature_dict.values():
    geom =f.geometry()
    bboxbuffer = geom.boundingBox().buffer(0.4) # I added a buffer of 0.4 m around the bounding box in order to get buildings which are 0.4m apart - mainly this concerns the prefab blocks which have cracks between them
    intersecting_ids = index.intersects(bboxbuffer) # all intersecting ids are in intersecting_ids, including the feature itself
#    print intersecting_ids
    self_id = feature_dict.keys()[feature_dict.values().index(f)] # acces the id (key) if the feature itself see D:\VajniBelejki\GetDictionaryKeybyValuePython
#    print self_id
    intersecting_ids.remove(self_id) # remove the id of the feature itself from the intersecting_ids so intersecting ids now has only potential neighbours
#    print intersecting_ids
#    print ""
# so intersecting_ids has the intersecting id of the intersecting features
#in order to get them i have to call them with for intersecting_id in intersecting_ids:
#intersecting_f = feature_dict[intersecting_id] to get the corresponding
#features from the dict and then call .geometry on what I called to get the geometry 
#of the intersecting things
#

#In this section I use the variable "type" to find at the building level
#if a building is Freistened or Gereiht, by saying if all intersecting_ids sa disjoint, pishi Freistehend,
#ako dori edna udari na Gereiht, break i pishi type = "Gereihte"

    print "Feature: " + str(f[OBJECTID])
#    print "Intersecting IDs: " + str(intersecting_ids)
    type = "Freistehend"
    for intersecting_id in intersecting_ids: # here the intersecting Ids are already without the id of the feature itself
#        print "Check Intersecting FID: " + str(feature_dict[intersecting_id][OBJECTID])
        intersecting_f = feature_dict[intersecting_id] # The intersecting_f variable receives the features from the dictionary, but not as geometry yet!
        geombuff = geom.buffer(0.4,2) #A buffer to check if there is a "crack"
#        print buff
        if intersecting_f.geometry().disjoint(geombuff): #   if intersecting_f.geometry().disjoint(geom) Here the intersecting_f as geometries are checked whether they are disjoint
            type = "Freistehend" # So the intersecting_f is not connected to the buffer, Freistehend
        elif intersecting_f.geometry().intersects(geom):
            type = "Gereihte" #So the intersecting_f is connected to a feature (not buffer of a feature)
            break
        else:
            type = "Freistehend with Crack" # So the intersecting_f is intersecting the buffer, but not the feature itself - with crack
#    print "Building Type: " + str(type)
#    print ""
    
    #Then Loop through the Months
    YearQhm = 0  #IMPORTANT THIS IS THE TOTAL HEAT DEMAND FOR THE YEAR VARIABLE, WHICH IS SUMMED FOR ALL THE MONTHS BELOW
    for Monthsublist in Climate_data:
#        print Monthsublist
#    Here comes the nice part - Wall(Segment) calculation
#First if the building is "Freistehend"
        Building_Month_SegHt = 0
        Building_Month_SegExGains = 0 #FROM SEGMENTS!, ROOF IS CALCULATED DOWN WITH THE BUILDING CALCULATION
        if type == "Freistehend":
            for line in geom.asPolygon(): # For every Polyline in the geometry of the Polygon
                for p in range(len(line)-1):# For every point in every Polyline in the geometry of the Polygon, it is minus one, because the last point is the first (I suppose the polyline starts with point A and finishesh with point A, so it is there twice, but we need only the segments which if A is doubled are fewer by one)
#                    print "Segment" + str(p) # Print the segment Number, I do not correct for the 0 index
                    segment = QgsGeometry.fromPolyline([line[p],line[p+1]]) # modulo trick to tova e remainder (modulo) operator dava ti ostatuka pri delenie 5 % 2 e 1
                    segment_Length = segment.length()  #or the same thing = math.sqrt(line[p].sqrDist(line[p+1])), but this gives the distance between the points, no need I think, since I already got Qgis to see it as geometry
                    segment_area = segment_Length*f[Height]
                    Seg_pointA = segment.asPolyline()[0]
                    Seg_pointB = segment.asPolyline()[1]
                    Segment_azimuth = Seg_pointA.azimuth(Seg_pointB)
                    Segment_orientation = ""
                    if 45 < Segment_azimuth < 135:
                        Segment_orientation = 3 # North
                    elif 135 < Segment_azimuth < 180 or -180 < Segment_azimuth < - 135:
                        Segment_orientation = 4 # East
                    elif -135 < Segment_azimuth < - 45:
                        Segment_orientation = 6 # South
                    else:
                        Segment_orientation = 5 #West
#                    print Segment_orientation
#                  Now begins the Segment Heat Transmition Calcl. Have to copy this for the Cracks and MutualWalls
                    SegWallArea = segment_area * (1-f[WinWallRatio])
                    SegWindowArea = segment_area - SegWallArea
                    SegEnEfWall = SegWallArea * f[PerIns]
                    SegEnEfWin = SegWindowArea * f[PerEnEfWin]
                    SegWallNonEnEfArea = SegWallArea - SegEnEfWall
                    SegWinNonEnEfArea = SegWindowArea - SegEnEfWin
                    SegHt = Ht(f[EnEfWallsU],SegEnEfWall)+Ht(f[EnEfWindowsU],SegEnEfWin)+Ht(f[WallU],SegWallNonEnEfArea)+Ht(f[WindowU],SegWinNonEnEfArea)
                    SegExGains = SG(Monthsublist[Segment_orientation],SegWindowArea,SolarGainsFactor) #Only Transparent Surfaces...)
                    Building_Month_SegHt += SegHt
                    Building_Month_SegExGains += SegExGains
#                    print "Segment Lenght:" + str(segment_Length)
#                    print "Segment Area:" + str(segment_area)
#                    print "SegWallArea:" + str(SegWallArea)
#                    print "SegWindowArea:" + str(SegWindowArea)
#                    print "SegEnEfWall:" + str(SegEnEfWall)
#                    print "SegEnEfWin:" + str(SegEnEfWin)
#                    print "SegWallNonEnEfArea:" + str(SegWallNonEnEfArea)
#                    print "SegHt:" + str(SegHt)
#                    print Monthsublist[Segment_orientation]
#                    print "SegExGains:" + str(SegExGains)
#                    print "Segment End"
#                    print ""
                    
#            print ""
        else:
            for line in geom.asPolygon(): 
                for p in range(len(line)-1):
                    # Lenght and Type Calculation
#                    print "Segment" + str(p) 
                    segment = QgsGeometry.fromPolyline([line[p],line[p+1]]) # In two lines after: the segment is a geometry, so a .lenght could be called, or .asPolyline()
    #              print math.sqrt(line[p].sqrDist(line[(p+1)])) # Either this or segment.lenght... :D
                    segmentbuff = segment.buffer(0.4,0) # The segment buffer is defined to check for "cracks"
                    segment_Length = segment.length() # the lenght of the segment goes into the variable Segment_Lenght
                    segment_area = segment_Length*f[Height]
#                    print segment_Length
                    segment_type = "Outer Wall"
                    Seg_pointA = segment.asPolyline()[0]
                    Seg_pointB = segment.asPolyline()[1]
                    MidPoint = midpoint(Seg_pointA, Seg_pointB)
#                    print MidPoint
                    MutualWallDifference = 0
#                    print "CHECK" #Just to check if the above works out
#                    print MutualWallDifference
                    #HERE THE SEGMENTS ARE CATEGORIZED
                    for intersecting_id in intersecting_ids: # Check all the neighbouring buildings (I know that these are "kalkanni"
                        intersecting_f = feature_dict[intersecting_id] # intersecting_f becomes a feature by getting its value from the dictionary with the key - intersecting_id , still needs .geometry()!
#                        print "Check FID: " + str(intersecting_f[OBJECTID]) # Print the FID of the neidhbouring building we are checking in the moment
                        inters_segment = segment.intersection(intersecting_f.geometry()) # inters_segment is the the geometry which is the intersection between the segment I am looking into and one of the nighbouring buildings, so if it is empty, the segment does not touch this neighbour, if not, it give back a "copy" of the segment itself, with its lenght and position. (I say give the intersection between the segment and the building, if there is such it could be the same as the segment, or smaller!)
                        inters_buffsegment = intersecting_f.geometry().intersection(segmentbuff) # it is the part of the intersecting_f that intersects with the segment buffer
                        buff_inters_buffsegment = inters_buffsegment.buffer(0.4,0) # So this is the buffer around the part of the intersecting id that intersects with the buffer of the segment.
                        if inters_segment.equals(segment): #if the inters_segment is equal to the segment, then it is a Mutual Wall
                            segment_type = "Mutual Wall"
#                            print segment_type
                            if f[Height] <= intersecting_f[Height]:
                                MutualWallDifference =0 #This is here in order to then compare the height of the segment and the Mutual Wall of the neighbouring Feature and see if it is more/less of it
                            else:
                                MutualWallDifference = f[Height] - intersecting_f[Height]
                            break
                        elif intersecting_f.geometry().intersects(segmentbuff) and buff_inters_buffsegment.contains(MidPoint): # So if the intersecting segment is not the same as the segment, then check if the intersecting_f intersects with the buffer of the segment and in the same time does not intersect the segment itsefl - if True - it is a Crack. The "and not" part is there to make sure that no segment perpendicular to a mutual wall is picked as a Mutual Wall itself (it is this intersection problem..)
                            segment_type = "Crack between Buildings"
#                            print segment_type
                        else:
                            segment_type = "Outer Wall"
#                            print segment_type
    #                        print "Problem, the whole wall is marked as Mutual Wall, when it has a part outside"
    #                        print inters_segment.length()
    #                        print inters_segment.asPolyline()
    #                        print segment_Length
    #                    Now I have to see how to cope with a segment when two buildings, share a wall but are of different height
    #                    I think the best way would be to say that all segments are OuterWalls, but for these that are Mutual, when calculating the area I will take the difference between the height of the segment and the neighbouring building, if they are the same height then the area would segmnt * 0 = 0, so I am in the clear
    #                    Also the small holes between the big residential buildings - there is indeed transmission from them, but no solar gains...
#                    print "Overall Segment Type:" + str(segment_type)
                    #HERE THE CATEGORIZATION ENDS AND SEGMENT HEAT CALCULATION BEGINS

                    #Orientation Calculation only if type == Outer Wall, then + Segment Ht and ExternalGains- 
                    if segment_type == "Outer Wall":
                        Segment_azimuth = Seg_pointA.azimuth(Seg_pointB)
                        Segment_orientation = ""
                        if 45 < Segment_azimuth < 135:
                            Segment_orientation = 3 # North
                        elif 135 < Segment_azimuth < 180 or -180 < Segment_azimuth < - 135:
                            Segment_orientation = 4 # East
                        elif -135 < Segment_azimuth < - 45:
                            Segment_orientation = 6 # South
                        else:
                            Segment_orientation = 5 #West - They are mingled since the sequence is N,E,W,S in the Naredba
#                        print Segment_orientation
                        SegWallArea = segment_area * (1-f[WinWallRatio])
                        SegWindowArea = segment_area - SegWallArea
                        SegEnEfWall = SegWallArea * f[PerIns]
                        SegEnEfWin = SegWindowArea * f[PerEnEfWin]
                        SegWallNonEnEfArea = SegWallArea - SegEnEfWall
                        SegWinNonEnEfArea = SegWindowArea - SegEnEfWin
                        SegHt = Ht(f[EnEfWallsU],SegEnEfWall)+Ht(f[EnEfWindowsU],SegEnEfWin)+Ht(f[WallU],SegWallNonEnEfArea)+Ht(f[WindowU],SegWinNonEnEfArea)
                        SegExGains = SG(Monthsublist[Segment_orientation],SegWindowArea,SolarGainsFactor) #Only Transparent Surfaces...)
                        Building_Month_SegHt += SegHt
                        Building_Month_SegExGains += SegExGains
#                        print "Segment Lenght:" + str(segment_Length)
#                        print "Segment Area:" + str(segment_area)
#                        print "SegWallArea:" + str(SegWallArea)
#                        print "SegWindowArea:" + str(SegWindowArea)
#                        print "SegEnEfWall:" + str(SegEnEfWall)
#                        print "SegEnEfWin:" + str(SegEnEfWin)
#                        print "SegWallNonEnEfArea:" + str(SegWallNonEnEfArea)
#                        print "SegHt:" + str(SegHt)
#                        print Monthsublist[Segment_orientation]
#                        print "SegExGains:" + str(SegExGains)
#                        print "Segment End"
#                        print ""
                    elif segment_type == "Mutual Wall": 
                        SegWallArea = segment_Length*(f[Height]-MutualWallDifference)
                        SegHt = Ht(f[WallU],SegWallArea)
                        Building_Month_SegHt += SegHt
                    elif segment_type == "Crack between Buildings":
                        SegWallArea = segment_Length*f[Height]
                        SegHt = Ht(f[WallU],SegWallArea)
                        Building_Month_SegHt += SegHt
#                    print "Segment End"
#                    print ""
                    
        #HERE BEGINS THE BUILDING LEVEL CALCULATION - FOR EACH MONTH
        #The Building_Month_Ht and ExGains are taken from the segment calculation, the rest of the calculations for a given building for a given month is here
        
        #Heat Losses
        if f[RoofType] == "hip": #This is to check if the roof is under a nonheated space or if it borders outside air, the temperatures for the unheated space are APPLIED ONLY HERE - 10 and 5 degrees!
            Building_Loss_Unheated_Space = Hu(f[Area],f[BaseU],f[Temperature],Monthsublist[1],10) + Hu(f[Area],f[RoofU],f[Temperature],Monthsublist[1],10)
        else:
            Building_Loss_Unheated_Space = Hu(f[Area],f[BaseU],f[Temperature],Monthsublist[1],10) + (f[Area]*f[RoofU])
#        print Hu(f[Area],f[BaseU],Monthsublist[1],f[Temperature],10)
#        print Hu(f[Area],f[RoofU],Monthsublist[1],f[Temperature],5)
#        print Building_Month_Ht
#        print Building_Loss_Unheated_Space
        Building_Loss_ThermalBridges = HtbSimple(f[Perimeter]*f[Height]+2*f[Area])
        Building_Month_TotalHt = Building_Month_SegHt + Building_Loss_Unheated_Space + Building_Loss_ThermalBridges#Add the roofs and Base(Hu) to the Building Ht - Building_Month_TotalHt + the Thermal Bridges
        Building_Month_Hv = Hv(f[Area]*f[Height],f[AirChangeRate],f[HeatedVolumeCoef]) #Might Add the Hipped Roof volume here, at some point, although it is not heated or ventilated, so no need...
        Hm = Building_Month_Hv+Building_Month_TotalHt
        Building_Month_Qlm = Qlm(Hm,f[Temperature],Monthsublist[1],Monthsublist[0]) #Monthsublist[1] = Outside Temp in the month, from the Climate_data List
#        print Building_Month_Hv
#        print Building_Month_TotalHt
#        print "Hm" + str(Hm)
#        print "Building_Month_Qlm:" + str(Building_Month_Qlm)
        
        #Heat Gains
        RoofSolarGains = 0 #f[Area]*Monthsublist[6] - Made it to zero, no gains from opaque surfaces
        Building_Month_TotalExGains = Building_Month_SegExGains + RoofSolarGains
        Building_Month_IG = IG(f[Floors],f[Area],f[InternalGainsPerSqMeter])
        Building_Month_Qgm = Qgm(Building_Month_TotalExGains,Building_Month_IG,Monthsublist[0]) #Monthsublist[0] = Days in the month according to the Climate_data
#        print "Building_Month_Qgm:" + str(Building_Month_Qgm)
#        print "Building_Month_Ht:" + str(Building_Month_Ht)
#        print "Building_Month_ExGains:" + str(Building_Month_ExGains)
#        print "Building_Month_Qgm:" + str(Building_Month_Qgm)
#        print ""

        #Utlization Factor
        UtilizationFactor = UtilFactor(Building_Month_Qgm,Building_Month_Qlm,Building_Month_TotalHt,Building_Month_Hv,f[Area]*f[Height])
        
        #MONTHLY BALANCE - EQUATION 1
        Qhm = Building_Month_Qlm - UtilizationFactor*Building_Month_Qgm
        YearQhm += Qhm
#        print "TOTAL MONTHLY DEMAND for Month  " + str(Climate_data.index(Monthsublist)+1) + " / " + str(Qhm) # OBSOLETE
        print "BUILDING REPORT FOR OBJECTID: " + str(f[OBJECTID])
        print "MONTH:" + str(Climate_data.index(Monthsublist)+1)
        print "LOSSES: ------------------------------------------------------"
        print "Transmission Losses - Outer Walls: " + str(int(Building_Month_SegHt)) + " W/K"
        print "Transmission Losses - Unheated Spaces (Hu): " + str(int(Building_Loss_Unheated_Space)) + " W/K"
        print "Transmission Losses - Thermal Bridges (Htb): " + str(int(Building_Loss_ThermalBridges))+ " W/K"
        print "Ventilation Losses (Hv): " + str(int(Building_Month_Hv)) + " W/K"
        print "Total Hm (Ht+Hv): " + str(int(Hm))+ " W/K"
        print "Total Heat Losses(Qlm): " + str(int(Building_Month_Qlm)) + " kWh/month"
        print "GAINS:---------------------------------------------------------"
        print "Solar Gains Facades: " + str(int(Building_Month_SegExGains)) + " W"
        print "Solar Gains Roof: " + str(int(RoofSolarGains)) + " W"
        print "Internal Gains: " + str(int(Building_Month_IG)) + " W"
        print "Total Gains: " + str(int(Building_Month_SegExGains+RoofSolarGains+Building_Month_IG)) + " W"
        print "Total Gains kWh/month(Qgm): " + str(int(Building_Month_Qgm)) + " KWh/month"
        print "-----------------------------------------------------------------"
        print "Utilization Factor for the month: " + str(UtilizationFactor)
        print "-----------------------------------------------------------------"
        print "Total Heat Demand for the month: " + str(int(Qhm))
        print "                                                         "
    f[TotalAnnualHeatDemand] = YearQhm
    f[TotalAnnualHeatDemandperSqMeter] = YearQhm / f[Area] / f[Floors]
    layer.updateFeature(f)
    print "==================================="
    print "Heat Demand per annum: " + str(int(YearQhm)) +" KWh/Annum"
    print "Demand Per Square Meter: "+ str(int(YearQhm / f[Area] / f[Floors])) +" KWh/Annum*m2"
    print 
#    print "New Feature"
layer.commitChanges()
toc=timeit.default_timer()
print "Time Elapsed in seconds:" + str(toc - tic)
    
    
    
    
    
    
