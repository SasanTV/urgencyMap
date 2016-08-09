""" rssReader.py reads given earthquake rss (Atom). If there is a new earthquake ID, the new event is added
    to the dictionary and its corresponding information is populated.
    Based on a threshold for mmi, the MBR corresponding to that threshold is assigned to each event
    This MBR can be used as a task region.

    Known bugs: if the earthquake is expanded in lon 180 to lon -180 area, the provided MBR is wrong.
    This case needs to be handled later."""

__author__ = "Sasan Tavakkol"
__email__ = "tavakkol@usc.edu"
__date__ = "04/01/2016"
API_KEY = "AIzaSyBD3ddBVLm7u9Am0gaO5Yfv4448fRkSJUk"

DEMO = True
SC = False
NC = (not SC)


import feedparser
import numpy as np
import urllib.request as ur # TODO: no need to import urllib and requests.
import requests
import io as StringIO
import zipfile
import threading
import datetime
from header import *

######Global Vars##########

#EarthquakeEvents is a dictionary to store events.
#Keys are earthquake ID's and values are EarthqaukeEvent's
earthqaukeEvents = {} #This can be loaded from a file when the code starts
silent = False
myheader= ""
THRESHOLD_MMI = 1  # This is threshold for earthquake intensity to create the task region.
POLLING_INTERVAL = 120  #  Interval for polling rss feed in seconds (The real interval will include the run time of the script).
                      #  Polling_Interval = 0 means no polling

def get_earthqaukeEvents():
    return earthqaukeEvents

def get_threshold_mmi():
    return THRESHOLD_MMI

def get_polling_interval():
    return POLLING_INTERVAL


def set_earthqaukeEvents(earthqauke_events):
    global earthqaukeEvents
    earthqaukeEvents = earthqauke_events

def set_threshold_mmi(threshold_mmi):
    global THRESHOLD_MMI
    THRESHOLD_MMI = threshold_mmi

def set_polling_interval(polling_interval):
    global POLLING_INTERVAL
    POLLING_INTERVAL = polling_interval


######## HELPER CLASSES/FUNCTIONS########


# Each new earthquake is stored as an EarthquakeEvent.
class EarthquakeEvent:
    def __init__(self, event_id = "", threshold_mmi = 0.0, intensity_xyz_URL = ""):
        self.event_id = event_id # event_id is the same as the key in EarthquakeEvents dictionary
        self.info = "" # info is the header of the file stored as a string
        self.lat = 0.0 
        self.lon = 0.0
        self.mag = 0.0 # Magnitude
        self.max_mmi = 0.0 # Instrumental Intensity
        self.event_add_utc_datetime = datetime.datetime.utcnow()
        self.event_happen_utc_datetime = ""
        self.MBR = Region() #Task region based on mmi threshold
        self.resetMBR()
        self.threshold_mmi = threshold_mmi
        self.intensity_xyz_URL = intensity_xyz_URL
        self.address_data = Address()
        self.shakeMap = np.array([])

        
    def populate(self,info): #Updates earthquakeEvent based on the self.info
        self.info = info
        MAG = 1; LAT = 2; LON = 3; # Constant Indecies
        YEAR = 6; MONTH = 4; DAY = 5; TIME = 7
        HOUR = 0; MIN = 1; SEC = 2
        info_split = self.info.split(" ")
        time_split = info_split[TIME].split(":")
        self.mag = float(info_split[MAG])
        self.lat = float(info_split[LAT])
        self.lon = float(info_split[LON])
        self.event_happen_utc_datetime = datetime.datetime(int(info_split[YEAR]),
                                        int(datetime.datetime.strptime(info_split[MONTH],'%b').month),
                                        int(info_split[DAY]),
                                        int(time_split[HOUR]),
                                        int(time_split[MIN]),
                                        int(time_split[SEC]))


        try:
            response = requests.get("https://maps.googleapis.com/maps/api/geocode/json?" \
                                    + "latlng=" + str(self.lat) +"," + str(self.lon) \
                                    + "&result_type=administrative_area_level_1&1&key=" + API_KEY)

            address_json = response.json()
            try:
                country_name = address_json["results"][0]["address_components"][1]["short_name"]

                if country_name == "US":
                    self.address_data.state = address_json["results"][0]["address_components"][0]["short_name"]
                else:
                    self.address_data.state = ""
                self.address_data.country = country_name
            except:
                self.address_data.country = "Country and state data not available."
                self.address_data.state = ""
        except:
            print("Address data not available")


            # eq.earthqaukeEvents[value].address_data["results"][0]["address_components"][3]["short_name"]
    def resetMBR(self): #Resets the MBR to values too large/too small to be a lat or lon
        self.MBR.topLeft.lon =  500.0
        self.MBR.topLeft.lat = -500.0
        self.MBR.bottomRight.lon = -500.0
        self.MBR.bottomRight.lat =  500.0

def get_xyz_link(event_id):
    if DEMO:
        if SC:
            return 'http://earthquake.usgs.gov/earthquakes/shakemap/sc/shake/'+event_id+'/download/grid.xyz.zip'
        elif NC:
            return 'http://earthquake.usgs.gov/earthquakes/shakemap/nc/shake/' + event_id + '/download/grid.xyz.zip'
    return 'http://earthquake.usgs.gov/earthquakes/shakemap/global/shake/'+event_id+'/download/grid.xyz.zip'
    

###################core function####################
def readRSS_newthread(url):
    threading.Timer(0, readRSS, [url]).start()

def readRSS (url):
    if DEMO:
        if SC:
            url = "file:///C:/Users/Sasan/Dropbox/MediaQ/codes/demo_sc.atom"
        else:
            url = "file:///C:/Users/Sasan/Dropbox/MediaQ/codes/demo_nc.atom"

    if (POLLING_INTERVAL):
        print ("Polling Interval is: " + str(POLLING_INTERVAL))
    else:
        print ("Polling has stopped.")
    if POLLING_INTERVAL:

        doc = feedparser.parse(url)
        for entry in doc.entries:
            print (entry.id)
            temp_id = entry.id.rsplit(':',1)[1]
            if (temp_id in earthqaukeEvents):
                if (not silent):
                    print (""+temp_id+" already exists in events list.")
                pass
            else:
                if (not silent):
                    print (""+temp_id+" added to events.")
                earthqaukeEvents[temp_id] = EarthquakeEvent(temp_id, THRESHOLD_MMI, get_xyz_link(temp_id))

                try:
                    response = ur.urlopen(earthqaukeEvents[temp_id].intensity_xyz_URL)
                    print(earthqaukeEvents[temp_id].intensity_xyz_URL)
                    zipHolder = StringIO.BytesIO (response.read())
                    zipFile = zipfile.ZipFile (zipHolder)
                    intensity_xyz_text = zipFile.read(zipFile.namelist()[0])
                    lines =  intensity_xyz_text.decode().split("\n")
                    HEADER = 0
                    earthqaukeEvents[temp_id].shakeMap = np.loadtxt(lines[HEADER+1:len(lines)]) #skips header.


                    earthqaukeEvents[temp_id].populate(lines[HEADER])
                    global myheader
                    myheader = lines[0]
                    LON = 0; LAT =1; MMI = 4;
                    max_mmi = -1 #Lower bound value for max_mmi
                    for line in lines [1:]:
                        data = line.split(" ")
                        if len(data) > MMI:
                            if float(data[MMI]) > earthqaukeEvents[temp_id].threshold_mmi:
                                if float(data[MMI]) > max_mmi:
                                    max_mmi = float(data[MMI])
                                if earthqaukeEvents[temp_id].MBR.topLeft.lon > float(data[LON]):
                                    earthqaukeEvents[temp_id].MBR.topLeft.lon = float(data[LON])
                                if earthqaukeEvents[temp_id].MBR.topLeft.lat < float(data[LAT]):
                                    earthqaukeEvents[temp_id].MBR.topLeft.lat = float(data[LAT])
                                if earthqaukeEvents[temp_id].MBR.bottomRight.lon < float(data[LON]):
                                    earthqaukeEvents[temp_id].MBR.bottomRight.lon = float(data[LON])
                                if earthqaukeEvents[temp_id].MBR.bottomRight.lat > float(data[LAT]):
                                    earthqaukeEvents[temp_id].MBR.bottomRight.lat = float(data[LAT])
                            else:
                                pass
                    earthqaukeEvents[temp_id].max_mmi = max_mmi
                    print('Maximum MMI: ' + str(max_mmi))



                except ur.HTTPError:
                    print('Error in reading intensity xyz file for '+temp_id+'. URL does not exists.')
        # To call readRSS every POLLING_INTERVAL seconds.
        threading.Timer(POLLING_INTERVAL, readRSS, [url]).start()

############## main() ####################
def main():
    # sample URLs
    significant_hour = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_hour.atom"
    significant_day = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_day.atom"
    plus_2_5_past_week = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.atom"
    significant_month = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.atom"

    # set to true to avoid prints
    # read RSS, and repeat every POLLING_INTERVAL seconds.
    readRSS (plus_2_5_past_week)

if __name__ == "__main__": main()
