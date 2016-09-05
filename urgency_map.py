import odbc
from scipy import interpolate
from header import *
import numpy as np
import matplotlib.pyplot as plt
from math import log, sqrt, floor, pi, radians, sin, cos, atan2
NUM_LEVELS = 4  # This is the number of levels in study, such as population, schools, bridges, etc.
THRESHOLD_YEAR_BUILDING = 2100
THRESHOLD_YEAR_BRIDGES  = 2100



class Urgency:
    def __init__(self):
        self.results = {}
        print ('Connecting to Hazus database ...')
        self.db = odbc.odbc('hazus64')
        self.cursor = self.db.cursor()
        print ('Connected.')
        self.intensity_mat = np.array([])  # initialization is not necessary, just for clarification
        self.exposure_mat = np.array([])  # initialization is not necessary, just for clarification
        self.damage_mat = np.array([])  # initialization is not necessary, just for clarification
        self.significance_mat = np.array([])  # initialization is not necessary, just for clarification
        self.urgency_mat = np.array([])  # initialization is not necessary, just for clarification
        self.urgency_mat_total = np.array([])  # initialization is not necessary, just for clarification
        self.delta_lat = 0
        self.delta_lon = 0
        self.delta_x = 0
        self.delta_y = 0

        # SIGNIFICANCE COEFS
        self.POP_SIGNIFICANCE_COEF = 1.0
        self.BRIDGES_SIGNIFICANCE_COEF = 1.0
        self.SCHOOLS_SIGNIFICANCE_COEF = 1.0

        # Index constants
        self.POP_L = 0
        self.SCHOOLS_L = 1
        self.BRIDGES_L = 2
        self.AREA_POP = 4
        self.LAT_POP = 5
        self.LON_POP = 6
        self.POP = 7
        self.BUILT_YEAR_POP = 8
        self.LAT_SCHOOLS = 6
        self.LON_SCHOOLS = 7
        self.NumStudent = 5
        self.BUILT_YEAR_SCHOOL = 4
        self.LAT_BRIDGES = 5
        self.LON_BRIDGES = 6
        self.BUILT_YEAR_BRIDGES = 3
        self.TRAFFIC = 4

    def __del__(self):
        print ('Closing Hazus connection...')
        self.db.close()
        print ('Connection closed.')

    # the following fragility curve is based on ATC-13 and is for masonry buildings.
    # year is not used.
    def damage_buildings(self, intensity ,year):
        p = 0
        mmi_ = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10 , 11, 12]
        moderate_ = [0, 0.08, 0.16, 0.24, 0.32, 0.4, 43.9, 89.1, 99.5, 100, 100, 100]
        # heavy_ = [0, 0.083, 0.167, 0.25, 0.333, 0.417, 0.5, 23.1, 77.1, 98, 99.9, 99.9]
        p = np.interp(intensity, mmi_, moderate_)/100.0 # p is the prob. of moderate damage
        return p

    # converts MMI to PGA based on USGS conversion table. PGA is in g units.
    def mmi_to_pga(self, mmi_in):
        pga_ = [0, 0.0017, 0.014, 0.039, 0.092, 0.18, 0.34, 0.65, 1.24]
        mmi_ = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        return np.interp(mmi_in, mmi_, pga_)


    def damage_bridges(self, intensity, year):
        pga = self.mmi_to_pga(intensity)
        pga_axis = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
        moderate_p_1964 = [0, 0.000299214, 0.045503399, 0.268634964, 0.55144542, 0.761634762, 0.890098311, 0.945862828, 0.979318619, 0.988052235, 0.998061422]
        moderate_p_1980 = [0, 0.001427301, 0.002854601, 0.006543569, 0.04741028, 0.191046992, 0.435781544, 0.675396219, 0.830377523, 0.926382276, 0.972502466]
        moderate_p_1990 = [0, 0.001338068, 0.002699666, 0.004061264, 0.03432003, 0.157957326, 0.383086783, 0.619501052, 0.796473195, 0.903093887, 0.958678318]
        moderate_p_1995 = [0, 0.002440745, 0.002753831, 0.003066916, 0.00663749, 0.056518262, 0.221982842, 0.489297011, 0.729482218, 0.878375177, 0.948899213]

        if year < 1980.0:
            p = np.interp(pga, pga_axis, moderate_p_1964)
        elif year >= 1980 and year < 1990:
            p = np.interp(pga, pga_axis, moderate_p_1980)
        elif year >= 1990 and year < 1995:
            p = np.interp(pga, pga_axis, moderate_p_1990)
        elif year >= 1995:
            p = np.interp(pga, pga_axis, moderate_p_1995)
        return p

    def urgency_map(self, MBR, state_US):
        WHERE_MBR_CLAUSE_CEN = ' WHERE [CenLat]>'+str(MBR.bottomRight.lat)+' AND [CenLat]<'+str(MBR.topLeft.lat)\
                            +' AND [CenLongit]>'+str(MBR.topLeft.lon)+' AND [CenLongit]<'+str(MBR.bottomRight.lon)
        WHERE_MBR_CLAUSE = ' WHERE [Latitude]>' + str(MBR.bottomRight.lat) + ' AND [Latitude]<' + str(MBR.topLeft.lat) \
                           + ' AND [Longitude]>' + str(MBR.topLeft.lon) + ' AND [Longitude]<' + str(MBR.bottomRight.lon)
        if(state_US == 'CA' or state_US == 'WA'):
            database_name = '[' + state_US + ']'
            query = 'SELECT CB.[OBJECTID]'\
                    ',CB.[CensusBlock]'\
                    ',CB.[Tract]'\
                    ',CB.[BldgSchemesId]'\
                    ',CB.[BlockArea]'\
                    ',CB.[CenLat]'\
                    ',CB.[CenLongit]'\
                    ',DB.[Population]' \
                    ',DB.[MedianYearBuilt]'\
                    ' FROM ' + database_name + '.[dbo].[hzCensusBlock] as CB'\
                    ' INNER JOIN ' + database_name + '.[dbo].[hzDemographicsB] as DB'\
                    ' ON CB.CensusBlock=DB.CensusBlock'\
                    + WHERE_MBR_CLAUSE_CEN
            self.cursor.execute(query)
            print(query)
            self.results['CensusBlocks'] = []
            while True:
                row = self.cursor.fetchone()
                if not row:
                    break
                self.results['CensusBlocks'].append(row)

            query = 'SELECT [OBJECTID]' \
                    ',[SchoolId]' \
                    ',[Name]' \
                    ',[PhoneNumber]' \
                    ',[YearBuilt]' \
                    ',[NumStudents]' \
                    ',[Latitude]' \
                    ',[Longitude]' \
                    ' FROM ' + database_name + '.[dbo].[hzSchool]' \
                    + WHERE_MBR_CLAUSE

            self.cursor.execute(query)
            print(query)
            self.results['Schools'] = []
            while True:
                row = self.cursor.fetchone()
                if not row:
                    break
                self.results['Schools'].append(row)

            query_select = 'SELECT [OBJECTID]' \
                    ',[Width]' \
                    ',[Length]' \
                    ',[YearBuilt]'\
                    ',[Traffic]' \
                    ',[Latitude]' \
                    ',[Longitude]'
            query_from_highway      = ' FROM ' + database_name + '.[dbo].[hzHighwayBridge]'
            query_from_railway      = ' FROM ' + database_name + '.[dbo].[hzRailwayBridge]'
            query_from_lightrailway = ' FROM ' + database_name + '.[dbo].[hzLightRailBridge]'

            query =   query_select + query_from_highway + WHERE_MBR_CLAUSE \
                    + " UNION " \
                    + query_select + query_from_railway + WHERE_MBR_CLAUSE \
                    + " UNION " \
                    + query_select + query_from_lightrailway + WHERE_MBR_CLAUSE

            self.cursor.execute(query)
            print(query)
            self.results['Bridges'] = []
            while True:
                row = self.cursor.fetchone()
                if not row:
                    break
                self.results['Bridges'].append(row)

        else:
            print("Error: Data not available for this state.")

    def intensity_map(self, shakeMap):
        print("Rendering intensity map ...")
        LON = 0; LAT = 1; MMI = 4

        lon_data = shakeMap[:, LON]
        lat_data = shakeMap[:, LAT]
        mmi_data = shakeMap[:, MMI]

        n_lon = 0
        while lat_data[n_lon] == lat_data[n_lon + 1]:
            n_lon += 1
        n_lon += 1
        n_lat = floor(len(shakeMap) / n_lon)
        if(floor(len(shakeMap) / n_lon) != len(shakeMap) / n_lon):
            print("Error in intensity map dimensions.")
        self.intensity_n_lon = n_lon
        self.intensity_n_lat = n_lat
        self.lon_axis = np.array(lon_data[0:n_lon])
        self.lat_axis = np.array(lat_data[0:len(lat_data):n_lon])  # lat_axis is in descending order.
        self.delta_lon = self.lon_axis[1] - self.lon_axis[0]
        self.delta_lat = self.lat_axis[1] - self.lat_axis[0]
        self.delta_x = distance_latlon(Point(lat=self.lat_axis[0], lon=self.lon_axis[0]),
                                       Point(lat=self.lat_axis[0], lon=self.lon_axis[1]))
        self.delta_y = distance_latlon(Point(lat=self.lat_axis[0], lon=self.lon_axis[0]),
                                       Point(lat=self.lat_axis[1], lon=self.lon_axis[0]))
        self.intensity_mat = np.reshape(mmi_data,(n_lat,n_lon))

        # plt.contourf(self.lon_axis,self.lat_axis,self.intensity_mat)
        # plt.show()

        self.exposure_map()

    #  exposure_map must run only after intensity_map.
    def exposure_map(self):
        print("Rendering urgency maps ...")
        self.exposure_mat = np.zeros((NUM_LEVELS,len(self.lat_axis),len(self.lon_axis)))
        self.damage_mat = np.zeros((NUM_LEVELS,len(self.lat_axis),len(self.lon_axis)))
        self.significance_mat = np.zeros((NUM_LEVELS,len(self.lat_axis),len(self.lon_axis)))

        print("    [Population] ...")

        total_population = 0
        for item in enumerate(self.results['CensusBlocks']):
            total_population += item[1][self.POP]
            h = sqrt(max(item[1][self.AREA_POP],0.000001)/pi)  # kilometers
            lat_index = int(round((item[1][self.LAT_POP] - self.lat_axis[0])/self.delta_lat))
            lon_index = int(round((item[1][self.LON_POP] - self.lon_axis[0])/self.delta_lon))
            half_num_horizontal_neighbors = int(floor(2.5*h/self.delta_x))
            horizontal_range = [min(max(lon_index - half_num_horizontal_neighbors, 0),len(self.lon_axis) - 1),
                                max(min(lon_index + half_num_horizontal_neighbors, len(self.lon_axis) - 1),0)]

            half_num_vertical_neighbors = int(floor(2.5*h/self.delta_y))
            vertical_range = [min(max(lat_index - half_num_vertical_neighbors, 0),len(self.lat_axis) - 1),
                              max(min(lat_index + half_num_vertical_neighbors, len(self.lat_axis) - 1),0)]
            w = np.zeros((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))
            sum_w = 0.0
            j_shifted = 0
            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    r = distance_latlon(Point(lat=self.lat_axis[i], lon=self.lon_axis[j]),
                                        Point(lat=item[1][self.LAT_POP],lon=item[1][self.LON_POP]))
                    temp_w = self.b_spline(r,h)
                    w[i_shifted][j_shifted] = temp_w
                    sum_w += temp_w
                    i_shifted += 1

                j_shifted += 1

            if(sum_w == 0.0):
                w = np.ones((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))

            sum_w = sum(sum(w))
            w = w / sum_w

            j_shifted = 0
            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    self.exposure_mat[self.POP_L][i][j] += w[i_shifted][j_shifted] * (item[1][self.POP])
                    scaled_i = int(round(i * self.intensity_n_lat / len(self.lat_axis)))
                    scaled_j = int(round(j * self.intensity_n_lon / len(self.lon_axis)))
                    mean_built_year = THRESHOLD_YEAR_BUILDING
                    temp_built_year = item[1][self.BUILT_YEAR_POP]
                    if (temp_built_year == None or temp_built_year < 1900 or temp_built_year > 2100):
                        temp_built_year = mean_built_year
                    self.damage_mat[self.POP_L][i][j] = max(self.damage_buildings(self.intensity_mat[scaled_i][scaled_j], temp_built_year)
                                                                , self.damage_mat[self.POP_L][i][j])

                    self.significance_mat[self.POP_L][i][j] = max(1
                                                                , self.significance_mat[self.POP_L][i][j])

                    i_shifted += 1
                j_shifted += 1
        print("sum distributed: " + str(sum(sum(self.exposure_mat[self.POP_L]))))
        print("sum original: " + str(total_population))
        """
        for j in range(0, len(self.lon_axis)):
            for i in range(0, len(self.lat_axis)):
                scaled_i = int(round(i * self.intensity_n_lat / len(self.lat_axis)))
                scaled_j = int(round(j * self.intensity_n_lon / len(self.lon_axis)))
                temp_coef = 1
                if (self.damage_mat[self.POP_L][i][j] > 0.0):
                    temp_coef = self.damage_mat[self.POP_L][i][j]
                self.damage_mat[self.POP_L][i][j] = temp_coef * self.intensity_mat[scaled_i][scaled_j]
        """

        print("    [Schools] ...")
        AREA_COEF = 0.0001
        total_population = 0
        for item in enumerate(self.results['Schools']):
            total_population += item[1][self.NumStudent]
            h = sqrt(AREA_COEF * max(item[1][self.NumStudent],1) / pi)  # kilometers
            lat_index = int(round((item[1][self.LAT_SCHOOLS] - self.lat_axis[0]) / self.delta_lat))
            lon_index = int(round((item[1][self.LON_SCHOOLS] - self.lon_axis[0]) / self.delta_lon))
            half_num_horizontal_neighbors = int(floor(2.5 * h / self.delta_x))
            horizontal_range = [min(max(lon_index - half_num_horizontal_neighbors, 0), len(self.lon_axis) - 1),
                                max(min(lon_index + half_num_horizontal_neighbors, len(self.lon_axis) - 1), 0)]

            half_num_vertical_neighbors = int(floor(2.5 * h / self.delta_y))
            vertical_range = [min(max(lat_index - half_num_vertical_neighbors, 0), len(self.lat_axis) - 1),
                              max(min(lat_index + half_num_vertical_neighbors, len(self.lat_axis) - 1), 0)]

            w = np.zeros((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))
            sum_w = 0
            j_shifted = 0
            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    r = distance_latlon(Point(lat=self.lat_axis[i], lon=self.lon_axis[j]),
                                        Point(lat=item[1][self.LAT_SCHOOLS], lon=item[1][self.LON_SCHOOLS]))
                    temp_w = self.b_spline(r, h)
                    w[i_shifted][j_shifted] = temp_w
                    sum_w += temp_w
                    i_shifted += 1
                j_shifted += 1

            if (sum_w == 0.0):
                w = np.ones((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))
            sum_w = sum(sum(w))
            w = w / sum_w

            j_shifted = 0

            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    self.exposure_mat[self.SCHOOLS_L][i][j] += w[i_shifted][j_shifted] * (item[1][self.NumStudent])
                    scaled_i = int(round(i * self.intensity_n_lat / len(self.lat_axis)))
                    scaled_j = int(round(j * self.intensity_n_lon / len(self.lon_axis)))

                    mean_built_year = THRESHOLD_YEAR_BUILDING
                    temp_built_year = item[1][self.BUILT_YEAR_SCHOOL]
                    if (temp_built_year == None or temp_built_year < 1900 or temp_built_year > 2100):
                        temp_built_year = mean_built_year
                    self.damage_mat[self.SCHOOLS_L][i][j] = max(self.damage_buildings(self.intensity_mat[scaled_i][scaled_j], temp_built_year)
                                                                , self.damage_mat[self.SCHOOLS_L][i][j])

                    self.significance_mat[self.SCHOOLS_L][i][j] = max(1
                                                                  , self.significance_mat[self.SCHOOLS_L][i][j])
                    i_shifted += 1
                j_shifted += 1
        print("sum distributed: " + str(sum(sum(self.exposure_mat[self.SCHOOLS_L]))))
        print("sum original: " + str(total_population))

        print("    [Bridges] ...")
        WIDTH = 1;
        LENGTH = 2;
        AREA_COEF = 0.000001 # m^2 to km^2
        total_population = 0
        mean_built_year = 1979.0 # np.average(self.results['Bridges'][self.BUILT_YEAR_BRIDGES]) # contains None values.
        for item in enumerate(self.results['Bridges']):
            total_population += 1 #item[1][self.TRAFFIC]
            h = sqrt(AREA_COEF * max(max(item[1][WIDTH],3)*item[1][LENGTH],1) / pi)  # kilometers
            lat_index = int(round((item[1][self.LAT_BRIDGES] - self.lat_axis[0]) / self.delta_lat))
            lon_index = int(round((item[1][self.LON_BRIDGES] - self.lon_axis[0]) / self.delta_lon))
            """containing_cell = Point()
            containing_cell.lat = self.lat_axis[round((item[1][LAT] - self.lat_axis[0]) / self.delta_lat)]
            containing_cell.lon = self.lon_axis[round((item[1][LON] - self.lon_axis[0]) / self.delta_lon)]"""
            half_num_horizontal_neighbors = int(floor(2.5 * h / self.delta_x))
            horizontal_range = [min(max(lon_index - half_num_horizontal_neighbors, 0), len(self.lon_axis) - 1),
                                max(min(lon_index + half_num_horizontal_neighbors, len(self.lon_axis) - 1), 0)]

            half_num_vertical_neighbors = int(floor(2.5 * h / self.delta_y))
            vertical_range = [min(max(lat_index - half_num_vertical_neighbors, 0), len(self.lat_axis) - 1),
                              max(min(lat_index + half_num_vertical_neighbors, len(self.lat_axis) - 1), 0)]

            w = np.zeros((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))
            sum_w = 0
            j_shifted = 0
            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    r = distance_latlon(Point(lat=self.lat_axis[i], lon=self.lon_axis[j]),
                                        Point(lat=item[1][self.LAT_BRIDGES], lon=item[1][self.LON_BRIDGES]))
                    temp_w = self.b_spline(r, h)
                    w[i_shifted][j_shifted] = temp_w
                    sum_w += temp_w
                    i_shifted += 1

                j_shifted += 1

            if (sum_w == 0.0):
                w = np.ones((vertical_range[1] - vertical_range[0] + 1, horizontal_range[1] - horizontal_range[0] + 1))
            sum_w = sum(sum(w))
            w = w / sum_w

            j_shifted = 0

            for j in range(horizontal_range[0], horizontal_range[1] + 1):
                i_shifted = 0
                for i in range(vertical_range[0], vertical_range[1] + 1):
                    self.exposure_mat[self.BRIDGES_L][i][j] += w[i_shifted][j_shifted] * 1 #(item[1][self.TRAFFIC])
                    scaled_i = int(round(i * self.intensity_n_lat / len(self.lat_axis)))
                    scaled_j = int(round(j * self.intensity_n_lon / len(self.lon_axis)))
                    temp_built_year = item[1][self.BUILT_YEAR_BRIDGES]
                    if (temp_built_year == None or temp_built_year < 1900 or temp_built_year > 2100):
                        temp_built_year = mean_built_year
                    self.damage_mat[self.BRIDGES_L][i][j] = max(self.damage_bridges(self.intensity_mat[scaled_i][scaled_j], temp_built_year)
                                                                  , self.damage_mat[self.BRIDGES_L][i][j])

                    self.significance_mat[self.BRIDGES_L][i][j] = max(item[1][self.TRAFFIC]+1
                                                                  , self.significance_mat[self.BRIDGES_L][i][j])

                    i_shifted += 1
                j_shifted += 1
        print("sum distributed: " + str(sum(sum(self.exposure_mat[self.BRIDGES_L]))))
        print("sum original: " + str(total_population))

        self.exposure_mat /= (self.delta_x*self.delta_y)

        self.significance_mat[self.POP_L]     *= self.POP_SIGNIFICANCE_COEF
        self.significance_mat[self.BRIDGES_L] *= self.BRIDGES_SIGNIFICANCE_COEF
        self.significance_mat[self.SCHOOLS_L] *= self.SCHOOLS_SIGNIFICANCE_COEF

        self.urgency_mat = self.damage_mat * self.exposure_mat * self.significance_mat

        epsilon = 0.0001
        self.urgency_mat[self.POP_L] /= np.max(np.max(np.max(self.urgency_mat[self.POP_L])), epsilon)
        self.urgency_mat[self.BRIDGES_L] /= np.max(np.max(np.max(self.urgency_mat[self.BRIDGES_L])), epsilon)
        self.urgency_mat[self.SCHOOLS_L] /= np.max(np.max(np.max(self.urgency_mat[self.SCHOOLS_L])), epsilon)

        self.urgency_mat_total = np.sum(self.urgency_mat, axis=0)
        self.urgency_mat_total /= np.max(np.max(np.max(self.urgency_mat_total)), epsilon) * 0.1


    def b_spline(self, r, h):
        R = r / h
        w = 0
        if (R < 1):
            w = 15 / (7 * pi * h ** 2) * (2 / 3 - R ** 2 + 1 / 2 * R ** 3)
        elif (1 <= R and R < 2):
            w = 15 / (7 * pi * h ** 2) * (1 / 6) * (2 - R) ** 3

        return w



