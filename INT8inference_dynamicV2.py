from openvino.runtime import Core
import cv2 as cv
import numpy as np
from dataset_img import FrameYUV, get_w_h, write_YUV420_Y, write_YUV420
import os
import math
import torch
import openvino.runtime as ov
import openvino.inference_engine as ie
import time


def calculate_psnr(img1, img2):
    mse = np.mean((img1 / 1.0 - img2 / 1.0) ** 2)
    if mse == 0:
        return 100
    PIXEL_MAX = 255.0
    return 20 * math.log10(PIXEL_MAX / math.sqrt(mse))

start_time = time.time()
# ie_core = ie.IECore()
ovrun_core = Core()
model_xml = './weights/Y52_8x1x160x160_int8.xml'
model_bin = './weights/Y52_8x1x160x160_int8.bin'
net = ovrun_core.read_model(model=model_xml)
# 设置动态形状
batch_size = 7
input_shape = (batch_size, 1, 1352, 2040)

batch_size_shape = (batch_size,)
net.reshape({'input_0': batch_size_shape, 'input_1': input_shape})
exec_net = ovrun_core.compile_model(model=net, device_name="CPU")

# output_layer = compiled_model.output(0)

# read YUV
qp_in = 37

img_list = ['02', '06', '08', '09', '11', '14', '15']
raw_list_y, com_list_y = [], []
raw_list_u, com_list_u = [], []
raw_list_v, com_list_v = [], []

for i in range(len(img_list)):
    raw_yuv_path = f'D:/dataset/DIV2K/yuv/valid/GT/08{img_list[i]}_2040x1352.yuv'
    com_yuv_path = f'D:/dataset/DIV2K/yuv/valid/QP{qp_in}/08{img_list[i]}_2040x1352.yuv'
    yuv_raw = open(raw_yuv_path, 'rb')
    yuv_compress = open(com_yuv_path, 'rb')
    wh = get_w_h(raw_yuv_path)
    yuv_raw_YUV = FrameYUV.read_YUV420(yuv_raw, wh[0], wh[1])
    yuv_cmp_YUV = FrameYUV.read_YUV420(yuv_compress, wh[0], wh[1])

    yuv_raw_y = yuv_raw_YUV._Y
    yuv_raw_u = yuv_raw_YUV._U
    yuv_raw_v = yuv_raw_YUV._V
    raw_list_y.append(yuv_raw_y)
    raw_list_u.append(yuv_raw_u)
    raw_list_v.append(yuv_raw_v)

    yuv_com_y = yuv_cmp_YUV._Y
    yuv_com_u = yuv_cmp_YUV._U
    yuv_com_v = yuv_cmp_YUV._V
    com_list_y.append(yuv_com_y)
    com_list_u.append(yuv_com_u)
    com_list_v.append(yuv_com_v)

com_list_y_input = np.array(com_list_y)
com_list_y_input = np.stack(com_list_y_input, axis=0)

com_list_y_input = np.expand_dims(com_list_y_input, 1).astype(np.float32) / 255.0

qp = np.array(qp_in) / 100.0
qp = np.repeat(qp, repeats=batch_size, axis=0)

output_blob = next(iter(exec_net.outputs))
result = exec_net([qp, com_list_y_input])[output_blob]
# result = exec_net.infer(inputs={'input_0': qp, 'input_1': com_list_y_input})[output_blob]
# result_out = compiled_model([qp, com_list_y_input])[output_layer]
out_y_list, enhance_psnr, unenhance_psnr = [], [], []

for i in range(batch_size):
    out_y = result[i, :, :, :]
    out_y = np.squeeze(out_y)
    out_y = np.clip(out_y, 0.0, 1.0)
    out_y = out_y * 255
    out_y = out_y.astype(np.uint8)
    enh_psnr = calculate_psnr(out_y, raw_list_y[i])
    unenh_psnr = calculate_psnr(com_list_y[i], raw_list_y[i])
    enhance_psnr.append(enh_psnr)
    unenhance_psnr.append(unenh_psnr)

unenhance_psnr_avg = sum(unenhance_psnr) / len(unenhance_psnr)
enhance_psnr_avg = sum(enhance_psnr) / len(enhance_psnr)
print(f'unEnhance PSNR : {unenhance_psnr}\n Enhance PSNR : {enhance_psnr}')

end_tmie = time.time()
execution_time = end_tmie - start_time
print(f" runtime toll : {execution_time}")
# write_YUV420(com_save_path, result_out, yuv_com_u, yuv_com_v)
