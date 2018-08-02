# coding:utf-8
#/usr/bin/python

import sys
import queue

import PyQt5
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QComboBox, QTextBrowser, QScrollBar, QHBoxLayout, QVBoxLayout

import pywinusb.hid as hid

# hid_device.vendor_id, hid_device.product_id

class Thread(QtCore.QThread):
    msg_ready = QtCore.pyqtSignal(list)

    def __init__(self, func):
        super(QtCore.QThread, self).__init__()
        self.func = func

    def run(self):
        while True:
            msg = []
            items = self.func()
            
            if items:
                for i in items:
                    msg.append(i)

                self.msg_ready.emit(msg)
            
class MainWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.currentDevice = 0   # 当前设备编号
        self.previewDevice = 0   # 之前设备编号

        self.HIDDevice = None    # 设备
        self.out_reports_id_list = []
        
        self.queue = queue.Queue()  #创建队列
        
        self.device_label = QLabel("Device List:")
        self.list = QComboBox()  #下拉列表

        self.baudrate_label = QLabel("Baudrate:")
        self.baudrate_list = QComboBox()
        self.baudrate_list.addItem("9600")
        self.baudrate_list.addItem("38400")
        self.baudrate_list.addItem("115200")
        self.baudrate_list.currentIndexChanged.connect(self.baudrate_change)

        self.openButton = QPushButton("Open")
        self.openButton.clicked.connect(self.device_open)
        
        self.rxClear = QPushButton("Clear")
        self.rxClear.clicked.connect(self.clearRxBrowser)

        layout_list = QHBoxLayout()

        layout_list.addWidget(self.device_label)
        layout_list.addWidget(self.list)
        layout_list.addWidget(self.baudrate_label)
        layout_list.addWidget(self.baudrate_list)
        layout_list.addWidget(self.openButton)
        layout_list.addWidget(self.rxClear)

        layout_list.addStretch()
        
        self.rxLine = QTextBrowser()

        self.bar    = QScrollBar()
        self.bar    = self.rxLine.verticalScrollBar()
        self.bar.setValue(self.bar.maximum());

        self.inputTips = QLabel("Info:")
        
        layout = QVBoxLayout()

        layout.addLayout(layout_list)
        layout.addWidget(self.rxLine)
        layout.addWidget(self.inputTips)
        
        self.setLayout(layout)

        filter = hid.HidDeviceFilter()
        self.all_devices = filter.get_devices()

        temp = 0
        for i in self.all_devices:
            id_information = "vId= 0x{0:04X}, pId= 0x{1:04X}, ppId= 0x{2:04X}".format(i.vendor_id, i.product_id, i.parent_instance_id)
            self.list.addItem(id_information)
            
            #select CP2110 if it existed
            if i.vendor_id == 0x10C4 and i.product_id == 0xEA80:
                self.list.setCurrentIndex = temp
                self.list.setItemText
                self.currentDevice = temp
        
            temp = temp + 1

        if self.all_devices:
            self.HIDDevice = self.all_devices[self.currentDevice]
            
        self.list.currentIndexChanged.connect(self.device_change)
        
        self.thread = Thread(self.queue_monitor)
        self.thread.msg_ready.connect(self.rxTextBrowserUpdate)
        self.thread.start()

    def queue_monitor(self):
        if self.queue.qsize():
            try:
                msgs = self.queue.get()
                return msgs

            except queue.Empty:
                pass

    string = ""
    def rxTextBrowserUpdate(self, item):
        if (item[0] == 1):
            if (item[1] == 10):
                self.rxLine.append(self.string)
                self.bar.setValue(self.bar.maximum())
                self.string = ""
            elif (item[1] != 13):    
                self.string = self.string + chr(item[1])
        
    def report_recv_handler(self, data):
        self.queue.put(data)
        
    def clearRxBrowser(self):
        self.rxLine.clear()
        
    def closeEvent(self, event):
        print("Close event")
        self.HIDDevice.close()

    def baudrate_change(self):
        print(self.baudrate_list.currentIndex())

    def device_change(self):
        self.currentDevice = self.list.currentIndex() #获取当前设备索引号
        
        if self.previewDevice != self.currentDevice:
            self.openButton.setText("Open")
            self.inputTips.setText("Info: ")
        else: 
            if self.HIDDevice.is_opened():
                self.openButton.setText("Close")
            else:
                self.openButton.setText("Open")

    def uart_onoff(self, onoff):
        buff    = [0x00] * 64
        buff[0] = 0x41 # Report ID = 0x41 Get/Set UART Enable

        if (onoff == 1):
            buff[1] = 0x1  # UART enable
        else:
            buff[1] = 0x0  # UART disable

        self.HIDDevice.send_feature_report(buff)

    def uart_config(self, baudrate):
        buff    = [0x00] * 64
        buff[0] = 0x50 # Report ID = 0x41 Get/Set UART Enable

        buff[1] = 0x0
        buff[2] = 0x0
        buff[3] = 0x25
        buff[4] = 0x80

        buff[5] = 0x0
        buff[6] = 0x0
        buff[7] = 0x3
        buff[8] = 0x0

        self.HIDDevice.send_feature_report(buff)

    def device_open(self):
        # 与之前选择的设备相同 
        if self.previewDevice == self.currentDevice:
            if self.HIDDevice.is_opened():
                self.HIDDevice.close()
                self.out_reports_id_list = []
                self.openButton.setText("Open")
                print(self.HIDDevice, "Closed")
                self.inputTips.setText("Info: ")
            else:
                self.HIDDevice.open()
                self.HIDDevice.set_raw_data_handler(self.report_recv_handler)
                self.reports = self.HIDDevice.find_output_reports()
                self.feature_report = self.HIDDevice.find_feature_reports()
                # in_reports   = self.HIDDevice.find_input_reports()

                self.uart_onoff(1)
                self.uart_config(9600)

                for i in self.feature_report:
                    print(i.get(False))
                
                for i in self.reports:
                    self.out_reports_id_list.append(i.report_id)
                
                self.inputTips.setText("Info: " + self.HIDDevice.product_name + " " + self.HIDDevice.vendor_name + " " + self.HIDDevice.serial_number)
                print(self.HIDDevice, "opend")
                
                self.openButton.setText("Close")
        else:
            self.HIDDevice.close()
            self.out_reports_id_list = []
            print(self.HIDDevice, "Closed")

            self.HIDDevice = self.all_devices[self.currentDevice]
            self.previewDevice = self.currentDevice
            self.HIDDevice.open()
            print(self.HIDDevice, "Opened")
            self.HIDDevice.set_raw_data_handler(self.report_recv_handler)
            self.reports = self.HIDDevice.find_output_reports()
            self.feature_report = self.HIDDevice.find_feature_reports()

            # in_reports   = self.HIDDevice.find_input_reports()
            
            self.uart_onoff(1)
            self.uart_config(9600)

            for i in self.feature_report:
                print(i)
                print(i.get(False))

            for i in self.reports:
                self.out_reports_id_list.append(i.report_id)

            self.inputTips.setText("Info: " + self.HIDDevice.product_name + " " + self.HIDDevice.vendor_name + " " + self.HIDDevice.serial_number)

            self.openButton.setText("Close")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    widget = MainWidget()

    widget.setWindowTitle("CP2110")
    widget.setGeometry(400, 300, 800, 600)
    widget.show()

    sys.exit(app.exec_())
    