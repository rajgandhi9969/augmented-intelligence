__author__="Raj Pradeep Gandhi"


from bs4 import BeautifulSoup
import geopy.distance
import statistics
import math


class Path:
    """
    This class have the properties of path we want to analyze. We will have total distance, max speed, stops and
    no_times_decelerations.
    """
    __slots__ = "total_distance","max_speed","median_speed","stops","no_times_deceleration","file_name"
    def __init__(self,total_distance=None,max_speed=None,median_speed=None,stops=None,no_times_deceleration=None,file_name=None):
        self.total_distance=total_distance
        self.max_speed=max_speed
        self.median_speed=median_speed
        self.stops=stops
        self.no_times_deceleration=no_times_deceleration
        self.file_name=file_name


def read_kml(filename):
    """
    This function reads the file and returns it beautiful soup object
    :param filename: name of file
    :return: beautiful soup object
    """
    with open(filename,"r") as kmlfile:
        soup=BeautifulSoup(kmlfile,"lxml")
        return soup


def getCordinates(soup):
    """
    This function reads the through the soup object and stores its data like lat,long and speed
    to an list and returns the list
    :param soup: soup object
    :return: list of coordinates and speed
    """
    coordinates_data=[]
    coordinates=soup.coordinates
    for child in coordinates.children:
        for line in child.split("\n"):
            if line.strip()!="":
                coordinates_data.append(line.split(","))
    return coordinates_data


def get_speed_correction(speedList,threshold=0.3):
    """
    The car speeds will be lower at the starting and the ending of the path.
    Stopping at the initial and final locat ion may be due to parking or some
    other issue rather than issue of path. Hence we few ignore initial and final speeds
    upto a threshold.
    This function returns the indices in the speed array which are to be considered
    to detect stop or shopping.
    :param speedList: list of all the speeds from start to end
    :param threshold: threshold speed which will be used to compare speeds
    :return: start and stop indices of speed array from which speed is to be considered
    """
    # i will be for start index and j will be for end index
    i=0
    j=len(speedList)-1
    start_speed=-1
    end_speed=math.inf
    while i<=j:
        current_speed_start=speedList[i]
        current_speed_end=speedList[j]
        if current_speed_start>=threshold and start_speed==-1:
            start_speed=i
        if current_speed_end>=threshold and end_speed==math.inf:
            end_speed=j
        if start_speed>-1 and end_speed<math.inf:
            return i,j
        i+=1
        j-=1
    # there will be cases in which our threshold will fail since car moving very slowly
    # thus we try lower threshold
    if i>j:
        if threshold==0.3:
            return get_speed_correction(speedList,0.25)
        elif threshold==0.25:
            return get_speed_correction(speedList,0.10)
        elif threshold==0.10:
            return get_speed_correction(speedList,0.03)
        elif threshold == 0.03:
            return get_speed_correction(speedList,0.02)
        else:
            return 0,len(speedList)-1


def checkWithinRITRadius(latitude,longitude):
    """
    This function checks if the car is in the 2 miles radius of RIT parking site.
    :param latitude: current latitude
    :param longitude: current longitude
    :return: True if car is within RIT parking site else false
    """
    radius_to_check=2 #2 miles radius
    RIT_center=(-77.679955,43.08611833333333)
    if geopy.distance.distance((RIT_center),(latitude,longitude)).miles<=radius_to_check:
        return True
    else:
        return False


def get_surrounding_coordinates(currentLong,currentLat,allData):
    """
    This function will the coordinates nearby to the given coordinates. Useful for detecting stops.
    :param currentLong: longitude
    :param currentLat: latitude
    :param allData: data of already seen latitude and longitude
    :return: coordinates if nearby exists else -1
    """
    surrounding_radius=0.1
    for locations in allData:
        if geopy.distance.distance((currentLong,currentLat),(locations))<=surrounding_radius:
            return locations
    return -1

def analyze(coordinates_data,filename,paths,soup):
    """
    This function reads the coordinates data and calculates the properties of path
    like no of stops, total distance and decelerations
    :param coordinates_data: list of coordinates and speed
    :param paths: list of path in which current path will be appended
    """
    stop_coordinates={}
    total_distance=0
    latitudes=[]
    longitudes=[]
    total_speed=[]
    decel_cordinates={}
    for coordinates in coordinates_data:
        """
        Get the latitude, longitude and speed in the array.
        """
        longitude=float(coordinates[0])
        latitude=float(coordinates[1])
        speed=float(coordinates[2])
        latitudes.append(latitude)
        longitudes.append(longitude)
        total_speed.append(speed)
    for i in range(len(latitudes)-1):
        lat1=latitudes[i]
        long1=longitudes[i]
        lat2=latitudes[i+1]
        long2=longitudes[i+1]
        # calculate distance only if car is not in RIT. Distance within RIT parking space
        # is not the correct measure of path
        if(not checkWithinRITRadius(lat1,long1)):
            # reference https://geopy.readthedocs.io/en/stable/#module-geopy.distance
            distance=geopy.distance.distance((lat1,long1),(lat2,long2)).miles
            total_distance+=distance
    max_speed=max(total_speed)
    # get speed by ignoring small stops at initial and final positions
    corrected_speed_start,corrected_speed_end=get_speed_correction(total_speed)
    correctedSpeedList=total_speed[corrected_speed_start:corrected_speed_end+1]
    # median speed
    median_speed=statistics.median_high(correctedSpeedList)
    for i in range(len(total_speed)-1):
        # detect stops. if nearby coordinate also has 0 speed. It means car has slowly moved to next lat and long.
        # this means car is still stopped at the signal, just moved a little bit. Hence we count all such coordinates
        # into one.
        if total_speed[i]==0.0 and (longitudes[i],latitudes[i]) not in stop_coordinates:
            checkSurrounding=get_surrounding_coordinates(longitudes[i],latitudes[i],stop_coordinates)
            if checkSurrounding==-1:
                stop_coordinates[(longitudes[i],latitudes[i])]=0
            else:
                stop_coordinates[checkSurrounding]+=1
        if total_speed[i]==0.0 and (longitudes[i],latitudes[i])  in stop_coordinates:
            stop_coordinates[(longitudes[i],latitudes[i])]+=1
        # detect decelerations.
        # considering change of 0.05 is not big change in speed
        if total_speed[i+1]+0.05<total_speed[i] and (longitudes[i],latitudes[i]) not in decel_cordinates:
            checkSurrounding=get_surrounding_coordinates(longitudes[i],latitudes[i],decel_cordinates)
            if checkSurrounding==-1:
                decel_cordinates[(longitudes[i],latitudes[i])]=0
            else:
                decel_cordinates[checkSurrounding] += 1
        if total_speed[i] == 0.0 and (longitudes[i], latitudes[i]) in decel_cordinates:
            decel_cordinates[(longitudes[i], latitudes[i])] += 1
    decelerations=len(decel_cordinates)
    print("total distance",total_distance,"miles")
    print("Max speed",max_speed)
    # print("stops-time function",stops)
    print("stops",len(stop_coordinates)-2)
    print("total decelerations",decelerations)
    print("Median speed",median_speed)
    print("Time taken",total_distance/median_speed)
    currentPath=Path(total_distance,max_speed,median_speed,len(stop_coordinates)-2,decelerations,filename)
    paths.append(currentPath)

def cost_function(allPaths):
    """
    This is the cost function which calculates the cost of all the paths given and prints the best
    path
    :param allPaths: array of path objects
    """
    cost_path={}
    current_best=None
    for path in allPaths:
        total_distance=path.total_distance
        max_speed=path.max_speed
        median_speed=path.median_speed
        stops=path.stops
        time=total_distance/median_speed
        cost=(3/5*(time/30))+(1/5*(stops/total_distance))+(1/5*((max_speed-median_speed)/52.13))
        cost_path[path.file_name]=cost
        if current_best==None:
            current_best=path.file_name
        else:
            if cost_path[current_best]>cost:
                current_best=path.file_name
    print("Best path ",current_best,"with cost",cost_path[current_best])


def main():
    """
    This is the main driver function which reads through all the kml files,
    and stores the path properties in the path list
    """
    paths = []
    filename="2019_04_09__1323_04.kml"
    print("***********Currently processing",filename,"***********")
    soup=read_kml(filename)
    coordinates=getCordinates(soup)
    analyze(coordinates,filename,paths,soup)
    cost_function(paths)


if __name__ == '__main__':
    main()

