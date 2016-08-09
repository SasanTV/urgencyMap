__author__ = "Sasan Tavakkol"
__email__ = "tavakkol@usc.edu"
__date__ = "04/05/2016"


import tkinter as tk
import earthquakes as eq
from header import *
import urgency_map as urg
import requests
import io as BytesIO
import numpy as np


import datetime as dt
#from mpl_toolkits.basemap import Basemap
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("TkAgg")

from math import log, sqrt



class EarthQuakeGui:
    def __init__(self, master, statusbar):
        self.urgency_map_instance = urg.Urgency()
        self.status = tk.StringVar()
        statusbar["textvariable"] = self.status
        self.last_update = "Unknown"

        self.label_padx = tk.Label(master, text="")
        self.label_padx.grid(row=0, column=0, sticky=tk.W, padx=3)

        self.button_run = tk.Button(master, text="Run", width=12, command=self.runEarthQuake)
        self.button_run.grid(row=4, column=2, sticky=tk.W)
        self.status.set(self.getStatus())

        self.label_list = tk.Label(master,text="Polling Interval (seconds):")
        self.label_list.grid(row=3,column=1, columnspan=2, sticky=tk.W)

        self.polling_interval = tk.IntVar()  # seconds
        self.entry_polling_interval = tk.Entry(master, textvariable=self.polling_interval, width=12)
        self.polling_interval.set(5)
        self.entry_polling_interval.grid(row=4, column=1 ,sticky=tk.W)

        isScenario = ""
        if eq.DEMO:
            isScenario = " (Scenarios)"
        self.label_list = tk.Label(master,text="Events List" + isScenario,)
        self.label_list.grid(row=0, column=1, columnspan=2, sticky=tk.W)

        self.events_list = tk.Listbox(master, width=30)
        self.events_list.grid(row=1, column=1, columnspan=2, sticky=tk.W)
        self.events_list.bind('<<ListboxSelect>>',self.show_info)

        self.button_refresh_events_list = tk.Button(master, text="Refresh", width=12, command=self.refresh_events_list)
        self.button_refresh_events_list.grid(row=2,column=1,sticky=tk.W,pady=10)

        self.button_urgency_map = tk.Button(master, text="Urgency Maps", width=12, command=self.urgency_map)
        self.button_urgency_map.grid(row=2, column=2, sticky=tk.W,pady=10)

        """
        self.button_show_map = tk.Button(master, text="map", width=10, command=self.show_map)
        self.button_show_map.grid(row=2, column=1,sticky=tk.W)
        """

        self.label_info = tk.Label(master,text="",justify=tk.LEFT,anchor=tk.NW)
        self.label_info.grid(row=1,column=3,sticky=tk.NW, padx=20)

    def refresh_events_list(self):
        self.events_list.delete(0,tk.END)
        for event in eq.earthqaukeEvents:
            self.events_list.insert(tk.END,event)
    def write_to_file(self):
        np.savetxt('lat_axis.csv', self.urgency_map_instance.lat_axis, delimiter=',', fmt='%1.8e')
        np.savetxt('lon_axis.csv', self.urgency_map_instance.lon_axis, delimiter=',', fmt = '%1.8e')

        np.savetxt('population_damage.csv', self.urgency_map_instance.damage_mat[self.urgency_map_instance.POP_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('population_exposure.csv', self.urgency_map_instance.exposure_mat[self.urgency_map_instance.POP_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('population_significance.csv', self.urgency_map_instance.significance_mat[self.urgency_map_instance.POP_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('population_urgency.csv', self.urgency_map_instance.urgency_mat[self.urgency_map_instance.POP_L],
                   delimiter=',', fmt='%1.8e')

        np.savetxt('schools_damage.csv', self.urgency_map_instance.damage_mat[self.urgency_map_instance.SCHOOLS_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('schools_exposure.csv', self.urgency_map_instance.exposure_mat[self.urgency_map_instance.SCHOOLS_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('schools_significance.csv', self.urgency_map_instance.significance_mat[self.urgency_map_instance.SCHOOLS_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('schools_urgency.csv', self.urgency_map_instance.urgency_mat[self.urgency_map_instance.SCHOOLS_L],
                   delimiter=',', fmt='%1.8e')

        np.savetxt('bridges_damage.csv', self.urgency_map_instance.damage_mat[self.urgency_map_instance.BRIDGES_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('bridges_exposure.csv', self.urgency_map_instance.exposure_mat[self.urgency_map_instance.BRIDGES_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('bridges_significance.csv', self.urgency_map_instance.significance_mat[self.urgency_map_instance.BRIDGES_L],
                   delimiter=',', fmt='%1.8e')
        np.savetxt('bridges_urgency.csv', self.urgency_map_instance.urgency_mat[self.urgency_map_instance.BRIDGES_L],
                   delimiter=',', fmt='%1.8e')

        np.savetxt('urgency_total.csv', self.urgency_map_instance.urgency_mat_total, delimiter=',', fmt='%1.8e')


    def urgency_map(self):
        event_temp = eq.earthqaukeEvents[self.events_list.get(tk.ACTIVE)]
        state_US = event_temp.address_data.state
        self.urgency_map_instance.urgency_map(event_temp.MBR, state_US)
        self.urgency_map_instance.intensity_map(event_temp.shakeMap)

        plt.figure(1, figsize=(25, 15))
        x = []; y = []; color = []; area = []
        LAT = self.urgency_map_instance.LAT_POP
        LON = self.urgency_map_instance.LON_POP
        POP = self.urgency_map_instance.POP
        BUILT = self.urgency_map_instance.BUILT_YEAR_POP
        for item in  enumerate(self.urgency_map_instance.results['CensusBlocks']):
            x.append(item[1][LON])
            y.append(item[1][LAT])
            """
            if item[1][BUILT] == 0:
                #color.append(100 * (log(1980) - log(1900))) # if no data just put something!
                color.append(1980)
            else:
                #color.append(100*(log(item[1][BUILT]+1)-log(1900)))
                color.append(item[1][BUILT])
            """
            color.append(10*log(item[1][POP]+1))
            area.append(10 * log(item[1][POP] + 1))
        """
        plt.subplot(231)
        plt.title("Population and Built Year")
        plt.scatter(x, y, s=area, c=color, alpha=0.5)
        plt.axis([event_temp.MBR.topLeft.lon, event_temp.MBR.bottomRight.lon,
                  event_temp.MBR.bottomRight.lat, event_temp.MBR.topLeft.lat])
        plt.colorbar()

        x = []; y = []; color = []; area =[]
        LAT = self.urgency_map_instance.LAT_SCHOOLS
        LON = self.urgency_map_instance.LON_SCHOOLS
        NumStudent = self.urgency_map_instance.NumStudent
        for item in enumerate(self.urgency_map_instance.results['Schools']):
            x.append(item[1][LON])
            y.append(item[1][LAT])
            color.append(log(item[1][NumStudent]))
            area.append(10*sqrt(item[1][NumStudent]))

        plt.subplot(232)
        plt.title("Schools")
        plt.scatter(x, y, s=area, c=color, alpha=0.5)
        plt.axis([event_temp.MBR.topLeft.lon, event_temp.MBR.bottomRight.lon,
                  event_temp.MBR.bottomRight.lat, event_temp.MBR.topLeft.lat])
        plt.colorbar()

        x = []; y = []; color = []; area = []
        LAT = self.urgency_map_instance.LAT_BRIDGES
        LON = self.urgency_map_instance.LON_BRIDGES
        TRAFFIC = self.urgency_map_instance.TRAFFIC
        for item in enumerate(self.urgency_map_instance.results['Bridges']):
            x.append(item[1][LON])
            y.append(item[1][LAT])
            color.append(log(item[1][TRAFFIC]+1)*log(item[1][TRAFFIC]+1))

        plt.subplot(233)
        plt.title("Bridges")
        plt.scatter(x, y, s=200, c=color, alpha=0.5)
        plt.axis([event_temp.MBR.topLeft.lon, event_temp.MBR.bottomRight.lon,
                  event_temp.MBR.bottomRight.lat, event_temp.MBR.topLeft.lat])
        plt.colorbar()
        """
        self.write_to_file()

        NUM_COLOR_LEVELS = 500

        plt.subplot(431)
        plt.title("Population damage")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.damage_mat[self.urgency_map_instance.POP_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(432)
        plt.title("Schools damage")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.damage_mat[self.urgency_map_instance.SCHOOLS_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(433)
        plt.title("Bridges damage")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.damage_mat[self.urgency_map_instance.BRIDGES_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(434)
        plt.title("Population Exposure")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.exposure_mat[self.urgency_map_instance.POP_L],NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(435)
        plt.title("Schools Exposure")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.exposure_mat[self.urgency_map_instance.SCHOOLS_L],NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(436)
        plt.title("Bridges Exposure")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.exposure_mat[self.urgency_map_instance.BRIDGES_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(437)
        plt.title("Population Significance")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.significance_mat[self.urgency_map_instance.POP_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(438)
        plt.title("Schools Significance")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.significance_mat[self.urgency_map_instance.SCHOOLS_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(439)
        plt.title("Bridges Significance")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.significance_mat[self.urgency_map_instance.BRIDGES_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(4, 3, 10)
        plt.title("Population Urgency")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.urgency_mat[self.urgency_map_instance.POP_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.subplot(4, 3, 11)
        plt.title("Schools Urgency")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.urgency_mat[self.urgency_map_instance.SCHOOLS_L], NUM_COLOR_LEVELS)
        plt.colorbar()


        plt.subplot(4, 3, 12)
        plt.title("Bridges Urgency")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     self.urgency_map_instance.urgency_mat[self.urgency_map_instance.BRIDGES_L], NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.figure(2)

        plt.title("Total Urgency")
        plt.contourf(self.urgency_map_instance.lon_axis, self.urgency_map_instance.lat_axis,
                     np.sqrt(np.sqrt(np.abs(self.urgency_map_instance.urgency_mat_total))), NUM_COLOR_LEVELS)
        plt.colorbar()

        plt.figure(3)
        google_map_static_URL = 'http://maps.google.com/maps/api/staticmap?'\
                            'center='+str(event_temp.lat)+','+str(event_temp.lon)+\
                            '&zoom=8&size=400x400'
        response = requests.get(google_map_static_URL)
        a = plt.imread(BytesIO.BytesIO(response.content))
        plt.imshow(a)

        plt.show()

    """
    def show_map(self):

        event_temp = eq.earthqaukeEvents[self.events_list.get(tk.ACTIVE)]

        map = Basemap(llcrnrlon=event_temp.lon-1. , llcrnrlat=event_temp.lat-1., urcrnrlon=event_temp.lon+1., urcrnrlat=event_temp.lat+1.,
                    projection='mill', resolution='l')
        # plot coastlines, draw label meridians and parallels.
        map.drawcoastlines()
        map.drawparallels(np.arange(-90, 90, 30), labels=[1, 0, 0, 0])
        map.drawmeridians(np.arange(map.lonmin, map.lonmax + 30, 60), labels=[0, 0, 0, 1])
        map.drawmapboundary(fill_color='aqua')
        map.fillcontinents(color='coral', lake_color='aqua')


        x, y = map(event_temp.lon, event_temp.lat)

        map.scatter(x, y, marker='D', color='m')
        plt.show()
    """

    def show_info(self,event):
        w = event.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        self.label_info["text"] = "Location (lat,lon): " + str(eq.earthqaukeEvents[value].lat) + ", " + str(eq.earthqaukeEvents[value].lon)\
                                  + "\n" + "Magnitude : " + str(eq.earthqaukeEvents[value].mag) \
                                  + "\n" + "Date happened (UTC) : " + str(eq.earthqaukeEvents[value].event_happen_utc_datetime) \
                                  + "\n" + "Date added (UTC) : " + str(eq.earthqaukeEvents[value].event_add_utc_datetime) \
                                  + "\n\n" + "Task Region : "\
                                  + "\n" + "        TopLeft (lat,lon) >> " + str(eq.earthqaukeEvents[value].MBR.topLeft.lat) + ", " + str(eq.earthqaukeEvents[value].MBR.topLeft.lon) \
                                  + "\n" + "        BottomRight (lat,lon) >> " + str(eq.earthqaukeEvents[value].MBR.bottomRight.lat) + ", " + str(eq.earthqaukeEvents[value].MBR.bottomRight.lon) \
                                  + "\n" + eq.earthqaukeEvents[value].address_data.state


    def runEarthQuake(self):
        if self.button_run["text"] == "Run":
            self.last_update = dt.datetime.utcnow().strftime("%m/%d/%Y   %H:%M:%S UTC")
            print ("Earthquakes Polling is running")
            significant_month = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_month.atom"
            plus_2_5_past_week = "http://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_week.atom"
            eq.set_polling_interval(self.polling_interval.get())
            eq.readRSS_newthread(plus_2_5_past_week)
            self.button_run["text"] = "Stop"
        elif self.button_run["text"] == "Stop":
            print ("Earthquakes Polling has stopped")
            eq.set_polling_interval(0)
            self.button_run["text"] = "Run"
        self.status.set(self.getStatus())


    def getStatus(self):
        if self.button_run["text"] == "Run":
            return "Status: Stopped " + "(Last Poll: " + self.last_update + ")"
        elif self.button_run["text"] == "Stop":
            return "Status: Running"
        else:
            return "Unknown Error"

def main():

    WIDTH = 600
    HEIGHT = 350
    root = tk.Tk()
    root.geometry("600x350")

    root.title ("MediaQ Disaster Response Demo")

    mainFrame = tk.Frame(root, width=WIDTH, height=HEIGHT)
    mainFrame.pack(anchor="nw")

    status_text = tk.StringVar()
    statusbar = tk.Label(root, anchor='w', bd=1, relief= "sunken")
    statusbar.pack(side='bottom',fill='x')
    eartQuakeGui = EarthQuakeGui(mainFrame,statusbar)

    root.mainloop()

if __name__ == '__main__':
    main()

