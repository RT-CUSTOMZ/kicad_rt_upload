import wx
import wx.aui
import pcbnew
import os
from urllib.request import *
import urllib.parse

majorVersion = int(pcbnew.Version().split(".")[0]) 
FILEPATH = 'uv_export/'

class UploadDialog(wx.Dialog): 
   def __init__(self, parent, title): 
        super(UploadDialog, self).__init__(parent, title = title) 
        panel = wx.Panel(self) 

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        username_box = wx.BoxSizer(wx.VERTICAL)
        username_box.Add(wx.StaticText(panel, -1, "User Name"), flag = wx.ALIGN_LEFT)
        self.username = wx.TextCtrl(panel, size = (180, 30))
        username_box.Add(self.username, proportion = 0)
        hbox1.Add(username_box, border = 5, flag = wx.ALL)
        hbox1.AddSpacer(20)

        exposure_box = wx.BoxSizer(wx.VERTICAL)
        exposure_box.Add(wx.StaticText(panel, -1, "Exposure (seconds)"), flag = wx.ALIGN_LEFT)
        self.exposure = wx.SpinCtrl(panel, size = (120, 30), min = 1, max = 1200, initial = 50)
        exposure_box.Add(self.exposure, flag = wx.ALIGN_LEFT)
        hbox1.Add(exposure_box, border = 5, flag = wx.ALL)

        vbox.Add(hbox1)
        vbox.AddSpacer(20)

        x_offset_box = wx.BoxSizer(wx.VERTICAL)
        x_offset_box.Add(wx.StaticText(panel, -1, "X offset (mm)"), flag = wx.ALIGN_LEFT)
        self.x_offset = wx.SpinCtrl(panel, size = (120, 30), min = 0, max = 128, initial = 0)
        x_offset_box.Add(self.x_offset, flag = wx.ALIGN_LEFT)
        hbox2.Add(x_offset_box, border = 5, flag = wx.ALL)
        hbox2.AddSpacer(20)

        y_offset_box = wx.BoxSizer(wx.VERTICAL)
        y_offset_box.Add(wx.StaticText(panel, -1, "Y offset (mm)"), flag = wx.ALIGN_LEFT)
        self.y_offset = wx.SpinCtrl(panel, size = (120, 30), min = 0, max = 128, initial = 0)
        y_offset_box.Add(self.y_offset, flag = wx.ALIGN_LEFT)
        hbox2.Add(y_offset_box, border = 5, flag = wx.ALL)

        vbox.Add(hbox2, flag = wx.ALIGN_CENTER)
        vbox.AddSpacer(20)

        self.ok = wx.Button(panel, wx.ID_OK, label = "Upload", size = (70,30))
        self.cancel = wx.Button(panel, wx.ID_CANCEL, label = "Cancel", size = (70,30))
        confirmation_box = wx.BoxSizer(wx.HORIZONTAL)
        confirmation_box.Add(self.cancel, flag = wx.ALIGN_RIGHT|wx.ALL, border = 5)
        confirmation_box.Add(self.ok, flag = wx.ALIGN_RIGHT|wx.ALL, border = 5)

        vbox.Add(confirmation_box, flag = wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        vbox.SetMinSize((200, 0))
        panel.SetSizer(vbox)
        vbox.SetSizeHints(self)

        

class RtUvUploadPlugin(pcbnew.ActionPlugin):
    def defaults(self):
        """
        Method defaults must be redefined
        self.name should be the menu label to use
        self.category should be the category (not yet used)
        self.description should be a comprehensive description
          of the plugin
        """
        self.name = "Upload a Project to RT exposure service"
        self.category = "Read PCB"
        self.pcbnew_icon_support = hasattr(self, "show_toolbar_button")
        self.show_toolbar_button = True
        self.icon_file_name = os.path.join(
                os.path.dirname(__file__), 'icon.png')
        self.description = "Generate manufacturing data for RT Lab manufacturing process."

    def Run(self):
        # config = Config()
        pcb_file_name = pcbnew.GetBoard().GetFileName()
        if not pcb_file_name:
            wx.MessageBox('Please save the board file before generating manufacturing data.')
            return
        print(pcb_file_name)

        board = pcbnew.LoadBoard(pcb_file_name)
        pctl = pcbnew.PLOT_CONTROLLER(board)
        popt = pctl.GetPlotOptions()

        popt.SetOutputDirectory(FILEPATH)

        # wx.MessageBox("test")
        dlg = UploadDialog(None, "RT UV Upload")
        match dlg.ShowModal():
            case wx.ID_OK:
                generateGerberForUV(pctl, popt, board)
                # And now upload, display errors in message box if any
                uploadGerbers(dlg.username, dlg.exposure, dlg.x_offset, dlg.y_offset)
                


plugin = RtUvUploadPlugin()
plugin.register() 

def uploadGerbers(user, exposure, offset_x, offset_y):
    base_url = "http://10.10.13.190:8000/upload?"
    params = {}
    if user != "":
        params['user'] = user
    params['exposure'] = str(user)
    params['offset_x'] = offset_x
    params['offset_y'] = offset_y

    params['layer'] = 'Bottom'
    url = base_url + urllib.parse.urlencode(params)
    headers = {'Content-Type': 'text/plain'}
    # data = open(file=filepath_bottom)
    # Request(url, headers=headers, method="POST")

def generateGerberForUV(plotControl, plotOptions, board):

    plotOptions.SetMirror(False)
    plotOptions.SetPlotViaOnMaskLayer(True)

    plotOptions.SetPlotValue(False)
    plotOptions.SetPlotReference(False)

    plotOptions.SetDisableGerberMacros(False)
    plotOptions.SetUseGerberX2format(False)
    plotOptions.SetIncludeGerberNetlistInfo(False)

    # create the filler provide the board as a param
    filler = pcbnew.ZONE_FILLER(board)
    # use the filler to re-fill all Zones on the board.
    filler.Fill(board.Zones())

    if (majorVersion < 7):
        plotOptions.SetExcludeEdgeLayer(False)
        plotControl.SetLayer(pcbnew.F_Cu)
        plotControl.OpenPlotfile(
            "F.Cu.UV", pcbnew.PLOT_FORMAT_GERBER, "Top Copper UV")
        plotControl.PlotLayer()

        plotControl.SetLayer(pcbnew.B_Cu)
        plotControl.OpenPlotfile(
            "B.Cu.UV", pcbnew.PLOT_FORMAT_GERBER, "Bottom Copper UV")
        plotControl.PlotLayer()

    else:
        seq = pcbnew.LSEQ()
        seq.push_back(pcbnew.Edge_Cuts)
        seq.push_back(pcbnew.F_Cu)
        plotControl.SetLayer(pcbnew.F_Cu)
        plotControl.OpenPlotfile(
            "F.Cu.UV", pcbnew.PLOT_FORMAT_GERBER, "Top Copper UV")
        plotControl.PlotLayers(seq)

        seq = pcbnew.LSEQ()
        seq.push_back(pcbnew.Edge_Cuts)
        seq.push_back(pcbnew.B_Cu)
        plotControl.SetLayer(pcbnew.B_Cu)
        plotControl.OpenPlotfile(
            "B.Cu.UV", pcbnew.PLOT_FORMAT_GERBER, "Bottom Copper UV")
        plotControl.PlotLayers(seq)
   
def getGbrFilenames():
    from os import listdir
    from os.path import isfile, join
    files = [f for f in listdir(FILEPATH) if isfile(join(FILEPATH, f))]
