import exifread  #读取照片的信息的包
import json
import os
import xlwt
from pandas import DataFrame,Series
import pandas as pd
import requests
import time


# 根据文件夹名，改照片的名字
def change_photo_name(photo_file_path):
	for file in os.listdir(photo_file_path):
		wenjianjia = os.path.join(photo_file_path, file)
		if os.path.isdir(wenjianjia):
			cur_wenjianjia_name = file
			# 子文件的路径以及文件列表
			cur_wenjianjia = os.path.realpath(wenjianjia)
			cur_filelist= os.listdir(cur_wenjianjia)
			i =0
			for item in (cur_filelist):
				try:
					if item.endswith(".jpg") or item.endswith(".HEIC") or item.endswith(".JPG"):
						i=i+1
						src = os.path.join(os.path.abspath(cur_wenjianjia), item)
						dst = os.path.join(os.path.abspath(cur_wenjianjia), "%s"%cur_wenjianjia_name + "%s" % i + '.JPG')
						os.rename(src, dst)
				except:
					print("有问题的照片为")
					print(item)

# 读取原始的数据
def get_ori_data(file_path):
	f = open(file_path, 'rb')
	tag1 = exifread.process_file(f, details=False, strict=True)  # 只返回常用的exif信息
	tag = {}
	try:
		for key, value in tag1.items():
			print(key)
			if key not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):  # 去除四个不必要的exif属性，简化信息量
				if key == "GPS GPSLatitude":
					tag[key] = str(value)
				if key == "GPS GPSLongitude":
					tag[key] = str(value)
				if key =="Image DateTime":
					tag[key]=str(value)
	except:
		print(file_path)
	return tag

# 转化经纬度
def get_gps(dic):
	cur_dic ={}
	for key, value in dic.items():
		if key == "GPS GPSLatitude":
			cur_value = list(value.split("[")[1].split("]")[0].split(","))
			cur_value_first = float(cur_value[0])
			cur_value_second = float(cur_value[1])
			if "/"  in cur_value[2]:
				cur_value_third = float(cur_value[2].split("/")[0]) / float(cur_value[2].split("/")[1])
			else:
				cur_value_third =float(cur_value[2])
			cur_jindu = cur_value_second/60 + cur_value_third / 3600+cur_value_first
			cur_dic[key] = cur_jindu
		if key == "GPS GPSLongitude":
			cur_value = list(value.split("[")[1].split("]")[0].split(","))
			cur_value_first = float(cur_value[0])
			cur_value_second = float(cur_value[1])
			if "/" in cur_value[2]:
				cur_value_third = float(cur_value[2].split("/")[0]) / float(cur_value[2].split("/")[1])
			else:
				cur_value_third=float(cur_value[2])
			cur_weidu = cur_value_second/60 + cur_value_third / 3600+cur_value_first
			cur_dic[key] = cur_weidu
		if key=="Image DateTime":
			cur_time = value
			cur_dic[key] =cur_time
	return cur_dic

def get_picture_dic(file_path):
	picture_dic = {}
	# 遍历整个文件夹目录下的问文件
	for roadfilename in os.listdir(file_path):
		roadpathname = os.path.join(file_path, roadfilename)
		if os.path.isdir(roadpathname):
			# 如果是文件夹，则遍历文件中的内容
			cur_wenjianjia = os.path.realpath(roadpathname)
			for (root, dirs, files) in os.walk(file_path):
				# 遍历文件中的内容
				for filename in files:
					cur_path = os.path.join(root, filename)
					# 道路名称
					photo_name = filename.split(".")[0]
					try:
						ori_dic = get_ori_data(cur_path)
						gps_dic = get_gps(ori_dic)
						picture_dic[photo_name] = gps_dic
					except:
						print("error" + filename)
						print("--------------")
	return picture_dic

def save_to_excel(picture_dic,save_path):
	print(picture_dic)
	workbook = xlwt.Workbook(encoding='ascii')
	table = workbook.add_sheet("经纬度", cell_overwrite_ok=True)
	table.write(0, 0, "照片名称")
	table.write(0, 1, "具体位置")
	table.write(0, 2, "经度（高德坐标）")
	table.write(0, 3, "纬度（高德坐标）")
	table.write(0,4,"经度(84坐标)")
	table.write(0,5,"经度(84坐标)")
	table.write(0,6,"拍摄道路")
	# table.write(0, 6, "详细地址")
	# table.write(0,7,"街道")
	i = 0
    # 将初始文件写入至excel中
	for picture_key, picture_value in picture_dic.items():
		cur_image = picture_key
		cur_dic = picture_value
		table.write(i + 1, 0, cur_image)
		print(cur_image)
		cur_jingdu = cur_dic["GPS GPSLongitude"]
		cur_weidu = cur_dic["GPS GPSLatitude"]
		cur_time = cur_dic["Image DateTime"]
		
		# 转换坐标为高德坐标
		cur_gps_84 = str(cur_jingdu)+","+str(cur_weidu)
		print(cur_gps_84)
		cur_gps_gaode =transform_gps(cur_gps_84)
		cur_jindu_gaode = cur_gps_gaode.split(",")[0]
		cur_weidu_gaode =cur_gps_gaode.split(",")[1]
		# 根据高德坐标获取街道
		cur_address, cur_street = get_regeocode(cur_gps_gaode)
		table.write(i + 1, 1, cur_address)
		table.write(i + 1, 2, cur_jindu_gaode)
		table.write(i + 1, 3, cur_weidu_gaode)
		table.write(i + 1, 4, cur_jingdu)
		table.write(i + 1, 5, cur_weidu)
		table.write(i + 1, 6, cur_street)
		i = i + 1
		
	workbook.save(save_path)

def transform_gps(location):
    parameters = {'coordsys': 'gps', 'locations': location, 'key': '7ec25a333316bb26f0d25e9fdfa012b8'}
    base = 'http://restapi.amap.com/v3/assistant/coordinate/convert'
    response = requests.get(base, parameters)
    answer = response.json()
    gaode_jingweiud = answer["locations"]
    return answer['locations']

def get_regeocode(location):
    parameters = {'location': location, 'key': '4de0ecd325333306534160deafcdcafb'}
    base = 'http://restapi.amap.com/v3/geocode/regeo'
    response = requests.get(base, parameters)
    answer = response.json()
    print(answer)
    cur_address =  answer['regeocode']['formatted_address']
    cur_street = answer['regeocode']['addressComponent']["streetNumber"]["street"]
    cur_gaode_jingdu =location.split(",")[0]
    cur_gaode_weidu = location.split(",")[1]
    return cur_address, cur_street


# 读取文件
def Read_file(path):
	cur_excel = pd.read_excel(path,sheet_name=0)
	frame = DataFrame(cur_excel)
	print("----------------------------------------------------")
	print("表格的长度")
	print(len(frame))
	print("------------------------------------------------------")
	return frame


def Merge_data(jinwe_path, wenti_path,final_path):
	# 读取经纬度Excel
	# 读取存在问题的Excel
	frame_jinweidu = Read_file(jinwe_path)
	print("经纬度excel已读取")
	print("----------------------------------------------------")
	
	frame_wenti = Read_file(wenti_path)
	print("问题excel已读取")
	print("----------------------------------------------------")
	
	final = pd.merge(frame_jinweidu, frame_wenti, on="照片名称")
	final.sort_index(axis= 0,by="照片名称")
	print("已合并文件")
	print("----------------------------------------------------")
	print(final)
	final.to_excel(final_path, sheet_name="总表",index=False)
	print("已写入最终表格")
	print("----------------------------------------------------")
	
	""


