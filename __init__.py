from urllib.error import HTTPError
import wx
import wx.aui
import wx.adv
import pcbnew
import os
from urllib.request import *
import urllib.parse
from pathlib import Path

majorVersion = int(pcbnew.Version().split(".")[0]) 
FILEPATH = 'uv_export/'
BASE_URL = 'http://10.10.13.190:8000/'
DEFAULT_EXPOSURE = 60


def getProjectBasePath():
    board_path = pcbnew.GetBoard().GetFileName()
    parts = board_path.rpartition('/')
    return str(parts[0]+parts[1])

class UploadFinishedDialog(wx.Dialog):
    def __init__(self, parent, id1, id2):
        super(UploadFinishedDialog, self).__init__(parent, title = "Upload finished!")
        panel = wx.Panel(self)
        vbox = wx.BoxSizer(wx.VERTICAL)

        text = wx.StaticText(panel, -1, "Upload successful, view the status by following the links:")
        vbox.Add(text)
        id1_url = wx.adv.HyperlinkCtrl(panel, url = BASE_URL + 'status?upload_id=' + id1.decode())
        vbox.Add(id1_url)
        id2_url = wx.adv.HyperlinkCtrl(panel, url = BASE_URL + 'status?upload_id=' + id2.decode())
        vbox.Add(id2_url)
        panel.SetSizer(vbox)
        vbox.SetSizeHints(self)

        

class UploadDialog(wx.Dialog): 
    def __init__(self, parent, title, pctl, popt, board): 
        self.pctl = pctl
        self.popt = popt
        self.board = board
        super(UploadDialog, self).__init__(parent, title = title) 
        panel = wx.Panel(self) 

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)

        username_box = wx.BoxSizer(wx.VERTICAL)
        username_box.Add(wx.StaticText(panel, -1, "User/Project Name"), flag = wx.ALIGN_LEFT)
        self.username = wx.TextCtrl(panel, size = (180, 30))
        username_box.Add(self.username, proportion = 0)
        hbox1.Add(username_box, border = 5, flag = wx.ALL)
        hbox1.AddSpacer(20)

        exposure_box = wx.BoxSizer(wx.VERTICAL)
        exposure_box.Add(wx.StaticText(panel, -1, "Exposure (seconds)"), flag = wx.ALIGN_LEFT)
        self.exposure = wx.SpinCtrl(panel, size = (120, 30), min = 1, max = 1200, initial = DEFAULT_EXPOSURE)
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

        self.upload = wx.Button(panel, label = "Upload", size = (70,30))
        self.cancel = wx.Button(panel, wx.ID_CANCEL, label = "Cancel", size = (70,30))
        confirmation_box = wx.BoxSizer(wx.HORIZONTAL)
        confirmation_box.Add(self.cancel, flag = wx.ALIGN_RIGHT|wx.ALL, border = 5)
        confirmation_box.Add(self.upload, flag = wx.ALIGN_RIGHT|wx.ALL, border = 5)

        vbox.Add(confirmation_box, flag = wx.ALIGN_BOTTOM|wx.ALIGN_RIGHT)
        vbox.SetMinSize((200, 0))
        panel.SetSizer(vbox)
        vbox.SetSizeHints(self)

        self.Bind(wx.EVT_BUTTON, self.onUploadClick, self.upload)
    def onUploadClick(self, event):
        generateGerberForUV(self.pctl, self.popt, self.board)
        # And now upload, display errors in message box if any
        ids = uploadGerbers(self.username.GetLineText(0), self.exposure.GetValue(), self.x_offset.GetValue(), self.y_offset.GetValue())
        if len(ids) == 2:
            UploadFinishedDialog(self, ids[0], ids[1]).ShowModal()
        self.EndModal(wx.ID_OK)


        

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

        board = pcbnew.LoadBoard(pcb_file_name)
        pctl = pcbnew.PLOT_CONTROLLER(board)
        popt = pctl.GetPlotOptions()

        popt.SetOutputDirectory(FILEPATH)

        if len(getProjectBasePath()) == 0:
            wx.MessageBox("Failed to evaluate Project Base Path! Please restart KiCad!")
        dlg = UploadDialog(None, "RT UV Upload", pctl, popt, board)
        if dlg.ShowModal() == wx.ID_OK:
            # TODO
            return


plugin = RtUvUploadPlugin()
plugin.register() 

def uploadGerbers(user, exposure, offset_x, offset_y):
    ids = []

    params = {}
    if user != "":
        params['user'] = user
    params['exposure'] = exposure
    params['offset_x'] = offset_x
    params['offset_y'] = offset_y

    headers = {'Content-Type': 'text/plain'}
    gbrs = getFilePaths()
    if len(gbrs) == 0:
        wx.MessageBox("Can't find Gerber files for upload")
    for f in gbrs:
        with open(file=f, mode='r') as data:
            if f.name.endswith('TOP.gbr'):
                params['layer'] = 'Top'
            if f.name.endswith('BOT.gbr'):
                params['layer'] = 'Bottom'
            params['filename'] = f.name
            if not data.readable():
                wx.MessageBox("Error reading from "+f.name)
            url = BASE_URL + 'upload?' + urllib.parse.urlencode(params)
            req = Request(url, data=data, headers=headers, method="POST")
            try:
                resp = urlopen(req)
                if resp.status == 202:
                    ids.append(resp.read())
            except HTTPError as err:
                wx.MessageBox("Upload error, code "+str(err.code))
                return
            except:
                wx.MessageBox("Error uploading "+f.name+"\nServer not reachable?")
                return
            data.close()
    return ids

def getFilePaths():
    p = Path(getProjectBasePath()+FILEPATH)
    files = list(p.glob('**/*.gbr'))
    gerbers = []
    for f in files:
        if f.name.endswith('TOP.gbr'):
            gerbers.append(f)
        if f.name.endswith('BOT.gbr'):
            gerbers.append(f)
    return gerbers


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
            "TOP", pcbnew.PLOT_FORMAT_GERBER, "Top Copper UV")
        plotControl.PlotLayer()

        plotControl.SetLayer(pcbnew.B_Cu)
        plotControl.OpenPlotfile(
            "BOT", pcbnew.PLOT_FORMAT_GERBER, "Bottom Copper UV")
        plotControl.PlotLayer()

    else:
        seq = pcbnew.LSEQ()
        seq.push_back(pcbnew.Edge_Cuts)
        seq.push_back(pcbnew.F_Cu)
        plotControl.SetLayer(pcbnew.F_Cu)
        plotControl.OpenPlotfile(
            "TOP", pcbnew.PLOT_FORMAT_GERBER, "Top Copper UV")
        plotControl.PlotLayers(seq)

        seq = pcbnew.LSEQ()
        seq.push_back(pcbnew.Edge_Cuts)
        seq.push_back(pcbnew.B_Cu)
        plotControl.SetLayer(pcbnew.B_Cu)
        plotControl.OpenPlotfile(
            "BOT", pcbnew.PLOT_FORMAT_GERBER, "Bottom Copper UV")
        plotControl.PlotLayers(seq)
    plotControl.ClosePlot()
