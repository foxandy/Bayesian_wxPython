import numpy as np 
import json
import copy
import wx
import os

#global lists track loaded and created nodes for error checking and easy saving
nodesSave = []
parentsSave = []
statesSave = []
cptsSave = []
cpts = []
evidenceList=[]
marginals=[]

#The main frame - contains the menu bars
class DemoFrame(wx.Frame):
    """Main Frame holding the Panel."""
    def __init__(self, *args, **kwargs):
        """Create the DemoFrame."""
        wx.Frame.__init__(self, *args, **kwargs)

        self.Panel = MainPanel(self)
        self.Fit()
        
        self.CreateStatusBar(1)              
        fileMenu= wx.Menu()

        menuOpen = fileMenu.Append(wx.ID_ANY, "&Load"," Load a Network")
        
        # Add save and save as menu items
        menuSave = fileMenu.Append(wx.ID_ANY, "&Save"," Save the file")
        menuSaveAs = fileMenu.Append(wx.ID_ANY, "Save &As"," Save the file with a new name")
        fileMenu.AppendSeparator()
        menuAbout = fileMenu.Append(wx.ID_ABOUT, "A&bout"," Information about this program")
        menuExit = fileMenu.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)
        self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
        self.Bind(wx.EVT_MENU, self.OnSaveAs, menuSaveAs)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        
        editMenu = wx.Menu()
        menuNew = editMenu.Append(wx.ID_ANY, 'A&dd Node', 'Add a node to the network')
        menuChange = editMenu.Append(wx.ID_ANY, '&Edit Network', 'Edit nodes in the network')
        self.Bind(wx.EVT_MENU, self.OnNew, menuNew)
        self.Bind(wx.EVT_MENU, self.OnChange, menuChange)
        
        analysisMenu = wx.Menu()
        menuEvidence = analysisMenu.Append(wx.ID_ANY, '&Set Evidence', 'Set node evidence')
        menuClearEv = analysisMenu.Append(wx.ID_ANY, '&Clear Evidence', 'Clear evidence for all nodes')
        menuInfer = analysisMenu.Append(wx.ID_ANY, 'Perform &Inference', 'In')
        self.Bind(wx.EVT_MENU, self.OnInference, menuInfer)
        self.Bind(wx.EVT_MENU, self.OnEvidence, menuEvidence)
        self.Bind(wx.EVT_MENU, self.OnClearEvidence, menuClearEv)
        
        menuBar = wx.MenuBar()
        menuBar.Append(fileMenu,"&File")
        menuBar.Append(editMenu,"&Network")
        menuBar.Append(analysisMenu,"&Analyze")
        self.SetMenuBar(menuBar)
            
        self.dirname = ""
        self.filename = ""
        
    def OnNew(self,e):
        'Create a new node'
        tf = TextFrame()
        tf.Show()  
    
    def OnChange(self,e):
        'Edit an existing node'
        form = MyEditForm()
        form.Show()
            
    def OnEvidence(self,e):
        'Set evidence to a node'
        form = MyEvidenceForm()
        form.Show()
    
    def OnInference(self,e):
        'Complete inference calculation'
        if len(evidenceList) == 0:
            dlg = wx.MessageDialog(self,"Please add evidence before calculating inference!","Inference", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            ev = setEvidenceList(evidenceList)
            output, joint = doInference(cpts + ev)
            doInference(cpts + setEvidenceList(evidenceList))
            for x in output:
                marginals.append(x)
            #The list control, node illustration, and solution text require update
            self.Panel.bPanel.fillListCtrl()
            self.Panel.tPanel = TopPanel(frame.Panel)
            self.Panel.sPanel.fillText(joint)
    
    def OnClearEvidence(self,e):
        'Clear evidence from a single node'
        evidenceList.clear()
        marginals.clear()
        self.Panel.bPanel.fillListCtrl()
        self.Panel.tPanel = TopPanel(frame.Panel)
        self.Panel.sPanel.fillText('')
            
        
    def OnOpen(self,e):
        'Load a premade network'
        dlg = wx.FileDialog(self, "Choose a JSON file to import", defaultDir=self.dirname, 
                            defaultFile=self.filename, style=wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            clearAll()
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            fullname = os.path.join(self.dirname, self.filename)
            self.DisplayFilenameOnStatusBar() 
            load(fullname)
            #call the list control function to refill the list control
            self.Panel.bPanel.fillListCtrl()
            #remake the diagram panel with the new nodes
            self.Panel.tPanel = TopPanel(self.Panel)
            self.Panel.sPanel.fillText('')
        dlg.Destroy()

    def OnSave(self, event):
        'Save the network to JSON'
        if not self.filename:
            # if the name has not been set then ask for a name
            self.OnSaveAs(event)
            return 
        else:
            self.SetTemporaryStatus("File saved")
            fullname = os.path.join(self.dirname, self.filename)
            save(fullname)
            #f = open(fullname, 'w')
            #f.write(self.Panel.tCtrl.GetValue())
            #f.close()
            
    def OnSaveAs(self, event):
        'Open a file dialog and ask for a name'
        dlg = wx.FileDialog(self, "Choose a file", defaultDir=self.dirname, 
                            defaultFile=self.filename, style=wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            fullname = os.path.join(self.dirname, self.filename)
            self.DisplayFilenameOnStatusBar()
            # and now call the function that does the actual saving
            self.OnSave(event)
        dlg.Destroy()
        
    def OnAbout(self,e):
        dlg = wx.MessageDialog( self, "Welcome to the Bayesian Network Creator, built in Python 3.x. See documentation for details.", "About", wx.OK)
        dlg.ShowModal()
        dlg.Destroy()

    def OnExit(self,e):
        'Close the app'
        self.Close(True)
        
    def DisplayFilenameOnStatusBar(self):
        fullname = os.path.join(self.dirname, self.filename)
        self.SetStatusText(fullname, 0)       
    
    def SetTemporaryStatus(self, msg, duration=2000):
        self.SetStatusText(msg, 0)
        wx.CallLater(duration, self.DisplayFilenameOnStatusBar)

#The main panel holds the other three panels
class MainPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.tPanel = TopPanel(self)
        self.bPanel = BottomPanel(self)
        self.sPanel = SolutionPanel(self)


        Sizer = wx.BoxSizer(wx.VERTICAL)
        Sizer.Add(self.tPanel, 0, wx.ALIGN_TOP|wx.ALL, 0)
        Sizer.Add(self.bPanel, 1, wx.ALIGN_CENTER|wx.ALL, 0)
        Sizer.Add(self.sPanel, 2, wx.ALIGN_CENTER|wx.ALL, 0)

        self.SetSizerAndFit(Sizer)
        
#The network diagram sits in the Top Panel
class TopPanel(wx.Panel):

    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.panel = wx.Panel(self, size=(600,400))
        self.panel.Bind(wx.EVT_PAINT, self.on_paint)
        Sizer = wx.BoxSizer(wx.VERTICAL)
        Sizer.Add(self.panel, 1, wx.ALIGN_CENTER|wx.ALL, 0)
        self.SetSizerAndFit(Sizer)
    
    def on_paint(self,event):
        # establish the painting surface
        dc = wx.PaintDC(self.panel)
        # dc.SetPen(wx.Pen('blue', 4))
        # # draw a blue line (thickness = 4)
        # dc.DrawLine(50, 20, 300, 20)
        dc.SetPen(wx.Pen('black', 1))
        # draw a red rounded-rectangle
        # rect = wx.Rect(50, 50, 100, 100)
        # dc.DrawRoundedRectangleRect(rect, 50)
        # dc.DrawLabel("A", wx.NullBitmap, rect, alignment=100|100)
        # draw a red circle with yellow fill
        dc.SetBrush(wx.Brush('white'))
        # x = 250
        # y = 100
        # r = 50
        # dc.DrawCircle(x, y, r)
        # rect2 = wx.Rect(200, 50, 100, 100)
        # dc.DrawRoundedRectangleRect(rect2, 50)
        # dc.DrawText("C", 245, 95)
        # dc.DrawLabel("C", wx.NullBitmap, rect2, alignment=200)

        # rect3 = wx.Rect(125, 175, 100, 100)
        # dc.DrawRoundedRectangleRect(rect3, 50)
        # dc.DrawLabel("B", wx.NullBitmap, rect3, alignment=200)

        # dc.DrawLine(150, 100, 200, 100)
        # dc.DrawLine(190, 90, 200, 100)
        # dc.DrawLine(190, 110, 200, 100)

        # w = 50
        # x = 50
        # y = 100
        # z = 100
        # index = 0

        # for n in nodes:
        #     if parents[index] == None:
        #         rect = wx.Rect(w, x, y, z)
        #         dc.DrawRoundedRectangleRect(rect, 50)
        #         dc.DrawLabel(n, wx.NullBitmap, rect, alignment=100|100)
        #         # w += 150
        #     else:
        #         w = 50
        #         test = w
        #         rect = wx.Rect(w, x + 150, y, z)
        #         dc.DrawRoundedRectangleRect(rect, 50)
        #         dc.DrawLabel(n, wx.NullBitmap, rect, alignment=100|100)
        #         for p in parents[index]:
        #             dc.DrawLine(w + 50, x + 100, test + 50, x + 150)
        #             w += 150
        #     w += 150
        #     index += 1


        #nodes = [u'z', u'x', u'a', u'c', u'b', u'e', u'f']
        #parents = [[], [u'z'], [u'z'], [], [u'a', u'c'], [u'b'], [u'e']]
        #nodes = ['a', 'c', 'b']
        #parents = [[], [], ['a', 'c']]
        nodes = nodesSave
        parents = parentsSave

        x = 50
        y = 50
        level = 0
        w = 100
        z = 100
        rects = {}
        index = 0

        def drawNode(nodeName):
            rect = wx.Rect(x, y + (150 * level), w, z)
            dc.DrawRoundedRectangle(x, y + (150 * level), w, z, 50)
            #dc.DrawRoundedRectangleRect(rect, 50)
            dc.DrawLabel(nodeName, wx.NullBitmap, rect, alignment=100)

        def drawParentArrow(parentNode):
            # DrawLine arguments are two points: x1, y1, x2, y2
            # Parent node: [x, level]
            dc.DrawLine(parentNode[0] + 50, y + 100 + (150 * parentNode[1]), x + 50, y + (150 * level))
            dc.DrawLine(x + 50, y + (150 * level), x + 40, y - 10 + (150 * level))
            dc.DrawLine(x + 50, y + (150 * level), x + 60, y - 10 + (150 * level))

        for n in nodes:
            for p in parents[index]:
                # check if we need a new level
                if level != rects[p][1] + 1:
                    x = 50
                    level = rects[p][1] + 1
                drawParentArrow(rects[p])
            rects[n] = [x, level]
            #if 1 in cpts[index].table:
            #    dc.SetBrush(wx.Brush('green'))
            #drawNode(n)
            for item in evidenceList:
                if n in item:
                    dc.SetBrush(wx.Brush('green'))
            drawNode(n)
            #for item in evidenceList:
            #for key,value in item.items():
            dc.SetBrush(wx.Brush('white'))
            x += 150
            index += 1

#The list control with node details sits in the bottom panel
class BottomPanel(wx.Panel):
    def __init__(self, parent, *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        
        self.list_ctrl = wx.ListCtrl(self, size=(600,150),style=wx.LC_REPORT|wx.BORDER_SUNKEN)
        self.list_ctrl.InsertColumn(0, 'Name', width=100)
        self.list_ctrl.InsertColumn(1, 'States', width=150)
        self.list_ctrl.InsertColumn(2, 'Parents', width=100)
        self.list_ctrl.InsertColumn(3, 'Distribution', width=125)
        self.list_ctrl.InsertColumn(4, 'Inferred Distribution', width=125)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list_ctrl, 0, wx.ALL|wx.EXPAND, 5)
        self.SetSizerAndFit(sizer)
        
    def fillListCtrl(self):
        'ListCtrl depends on the contents of the global lists'
        self.list_ctrl.ClearAll()
        self.list_ctrl.InsertColumn(0, 'Name', width=50)
        self.list_ctrl.InsertColumn(1, 'States', width=100)
        self.list_ctrl.InsertColumn(2, 'Parents', width=100)
        self.list_ctrl.InsertColumn(3, 'Distribution', width=150)
        self.list_ctrl.InsertColumn(4, 'Inferred Distribution', width=150)
        index = 0
        for name in nodesSave:
            self.list_ctrl.InsertItem(index, name)
            self.list_ctrl.SetItem(index, 1, ', '.join(statesSave[index]))
            if index >= len(parentsSave):
                self.list_ctrl.SetItem(index, 2, 'None')
            elif len(parentsSave[index]) == 0:
                self.list_ctrl.SetItem(index, 2, 'None')
            else:
                self.list_ctrl.SetItem(index, 2, ', '.join(parentsSave[index]))
            convert = (str(w) for w in cptsSave[index])
            self.list_ctrl.SetItem(index, 3, ', '.join(convert))
            if len(marginals) > 0:
                convertMarginal = ('%.2f' % w for w in marginals[index])
                self.list_ctrl.SetItem(index, 4, ', '.join(convertMarginal))
            index += 1

class SolutionPanel(wx.Panel):
    'Join probability solution is a Read-Only textbox'
    def __init__(self, parent,size = (600, -1), *args, **kwargs):
        wx.Panel.__init__(self, parent, *args, **kwargs)
        self.txtCtrl = wx.TextCtrl(self, size = (600, -1), style=wx.TE_MULTILINE)
        #make it read only
        self.txtCtrl.SetEditable(False)
        #make it a different shade to stand out
        self.txtCtrl.SetBackgroundColour((193,205,193))
        Sizer = wx.BoxSizer(wx.VERTICAL)
        Sizer.Add(self.txtCtrl, 1, wx.ALIGN_CENTER|wx.ALL, 0)
        self.SetSizerAndFit(Sizer)
    
    def fillText(self, text):
        self.txtCtrl.Clear()
        self.txtCtrl.AppendText('Joint probability distribution:\n')
        self.txtCtrl.AppendText(text)
                
class TextFrame(wx.Frame):
    'Create a new node from scratch'
    def __init__(self):
        global nodeName,parentInput, stateNames, probInput
        wx.Frame.__init__(self, None, -1, 'Enter Node Information', size=(650, 170))
        panel = wx.Panel(self, -1) 
        nodeLabel = wx.StaticText(panel, -1, "Name:")
        nodeName = wx.TextCtrl(panel, -1, "", size=(175, -1))
        nodeName.SetInsertionPoint(0)
        parentLabel = wx.StaticText(panel, -1, "Parents:")
        parentInput = wx.TextCtrl(panel, -1, "None", size=(175, -1))
        nodeName.SetInsertionPoint(0)
        stateLabel = wx.StaticText(panel, -1, "States:")
        stateNames = wx.TextCtrl(panel, -1, "", size=(175, -1))
        nodeName.SetInsertionPoint(0)
        probLabel = wx.StaticText(panel, -1, "Probabilities:")
        probInput = wx.TextCtrl(panel, -1, "Marginal for Parent Nodes/Conditional for Child Nodes", size=(325, -1))
        nodeName.SetInsertionPoint(0)
        sizer = wx.FlexGridSizer(cols=4, hgap=6, vgap=6)
        sizer.AddMany([nodeLabel, nodeName, parentLabel, parentInput,stateLabel, stateNames,probLabel, probInput])
        panel.SetSizer(sizer)
        
        m_close = wx.Button(panel, wx.ID_CLOSE, "Save Node",pos=(530, 100))
        m_close.Bind(wx.EVT_BUTTON, self.OnClose)

        
    def OnClose(self, event):
        dlg = wx.MessageDialog(self,
             "Do you want to save this node?",
             "Confirm Save", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            nodesSave.append(nodeName.GetValue().strip())
            states = stateNames.GetValue().strip().split(",")
            statesSave.append(states)
            if parentInput.GetValue()=='None':
                #probs = probInput.GetValue().strip().split(",")
                #cProb=map(float,probs)
                cProb = eval(probInput.GetLineText(0))
                cptsSave.append(cProb)
                together = nodeName.GetValue().strip()
                parentsSave.append([])
                cpt = TablePotential(together,cProb)
                cpts.append(cpt)
            else:                
                parents = []
                parents = parentInput.GetValue().strip().split(",")
                parentsCopy = copy.deepcopy(parents)
                parentsSave.append(parentsCopy)
                #probs = probInput.GetValue().strip().split(",")
                #cProb=map(float,probs)
                cProb = eval(probInput.GetLineText(0))
                cptsSave.append(cProb)                
                parents.reverse() 
                parents = ''.join(parents)
                together = parents + nodeName.GetValue().strip()
                cpt = TablePotential(together,cProb)
                cpts.append(cpt)        
#           dlg.Destroy()
            frame.Panel.bPanel.fillListCtrl()
            frame.Panel.tPanel = TopPanel(frame.Panel)
            self.Close(True)   

#Form for editing nodes
class MyEditForm(wx.Frame):
    #----------------------------------------------------------------------
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Edit Network")
        global parentEdit, statesEdit,probsEdit, statesOriginal, probsOriginal
        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)
        wx.StaticText(panel, -1, "Select Node:")
        
        wx.StaticText(panel, -1, "Parent Node(s):",pos=(20,45))
        parentEdit=wx.TextCtrl(panel, -1, "",pos=(20,65), size=(175, -1), style=wx.TE_READONLY)
        
        wx.StaticText(panel, -1, "States:",pos=(20,100))
        statesEdit = wx.TextCtrl(panel, -1, "",pos=(20,120), size=(175, -1))
        
        wx.StaticText(panel, -1, "Marginal/Conditional Probabilities:",pos=(20,155))
        probsEdit = wx.TextCtrl(panel, -1, "",pos=(20,175), size=(350, -1))
        
        sampleList = []
        self.cb = wx.ComboBox(panel,
                              size=wx.DefaultSize,
                              choices=sampleList)
        self.widgetMaker(self.cb, nodesSave)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.cb, 5, wx.ALL, 18)
        panel.SetSizer(sizer)
        saveEdits = wx.Button(panel, wx.ID_CLOSE, "Save Edits",pos=(270, 370))
        saveEdits.Bind(wx.EVT_BUTTON, self.OnCloseEdits)
        delNode = wx.Button(panel, wx.ID_CLOSE, "Delete Node",pos=(175, 370))
        delNode.Bind(wx.EVT_BUTTON, self.OnCloseDelete)

    #----------------------------------------------------------------------
    def widgetMaker(self, widget, objects):
        """"""
        for obj in objects:
            widget.Append(obj)
        widget.Bind(wx.EVT_COMBOBOX, self.onSelect)

    #----------------------------------------------------------------------
    def onSelect(self, event):
        """"""
        global selection, parentList
       
        selection = self.cb.GetStringSelection()
        if parentsSave[nodesSave.index(self.cb.GetStringSelection())] is None:
            parentEdit.SetValue("None")
        else:    
            parentEdit.SetValue(", ".join(item for item in parentsSave[nodesSave.index(self.cb.GetStringSelection())]))
                    
        parentStateList=statesSave[nodesSave.index(self.cb.GetStringSelection())]
        statesEdit.SetValue(", ".join(item for item in parentStateList))
            
        probsList=cptsSave[nodesSave.index(self.cb.GetStringSelection())]
        #probsEdit.SetValue(", ".join(str(item) for item in probsList))
        probsEdit.SetValue(str(probsList))
            
    def OnCloseDelete(self, event):
        global statesEdit,probsEdit, parentList
        
        l=list(items for items in parentsSave if items is not None)
        parentList = list(par for sublist in l for par in sublist)
        
        if (selection in parentList):
            dlg = wx.MessageDialog(self,
             "This is a Parent node with dependencies. Delete Child nodes before Parent Nodes!",
             "Node Deletion", wx.OK|wx.CANCEL|wx.ICON_QUESTION)            
            dlg.ShowModal()
            dlg.Destroy()
        else:
            dlg = wx.MessageDialog(self,
             "Are you sure you want to delete this node?",
             "Node Deletion", wx.OK|wx.CANCEL|wx.ICON_QUESTION)            
            result=dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_OK:    
                del statesSave[nodesSave.index(selection)]
                del cptsSave[nodesSave.index(selection)]
                del parentsSave[nodesSave.index(selection)]
                nodesSave.remove(selection)
                self.cb.Clear()
                parentEdit.SetValue("")
                statesEdit.SetValue("")
                probsEdit.SetValue("")
                self.widgetMaker(self.cb, nodesSave)
        frame.Panel.bPanel.fillListCtrl()
        frame.Panel.tPanel = TopPanel(frame.Panel)
        self.Close(True) 

            
    def OnCloseEdits(self, event):
        global statesSave, statesEdit,probsEdit, cptsSave
        dlg = wx.MessageDialog(self,
             "Network properties have changed! Do you want to save changes?",
             "Confirm Save", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            if selection in nodesSave:
                statesSave[nodesSave.index(selection)]=statesEdit.GetValue().strip().split(",")            
                #probs = probsEdit.GetValue().strip().split(",")
                #cProb=map(float,probs)
                cProb=eval(probsEdit.GetLineText(0))
                #cptsSave[nodesSave.index(selection)]=list(cProb)
                cptsSave[nodesSave.index(selection)]=cProb
                #print(statesSave)
                #print(cptsSave)
        frame.Panel.bPanel.fillListCtrl()
        frame.Panel.tPanel = TopPanel(frame.Panel)
        self.Close(True)   
#           dlg.Destroy()       

class MyEvidenceForm(wx.Frame):
    'Set evidence'
    #----------------------------------------------------------------------
    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "Edit Network")
        global statesEdit,probsEdit, statesOriginal, probsOriginal, nodesForEvid, evidenceIn
        # Add a panel so it looks the correct on all platforms
        panel = wx.Panel(self, wx.ID_ANY)
        wx.StaticText(panel, -1, "Available Nodes:", pos=(20,0))
        nodesForEvid=copy.deepcopy(nodesSave)
                
        wx.StaticText(panel, -1, "Available States for Selected Node:",pos=(20,55))
        statesEdit = wx.TextCtrl(panel, -1, "",pos=(20,75), size=(175, -1), style=wx.TE_READONLY)

        wx.StaticText(panel, -1, "Enter state with evidence:",pos=(20,100))
        evidenceIn = wx.TextCtrl(panel, -1, "",pos=(20,120), size=(350, -1))
                
        sampleList = []
        self.cb = wx.ComboBox(panel,
                              size=wx.DefaultSize,
                              choices=sampleList)
        self.widgetMaker(self.cb, nodesForEvid)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.cb, 5, wx.ALL, 18)
        panel.SetSizer(sizer)
        saveEvid = wx.Button(panel, wx.ID_CLOSE, "Set Evidence",pos=(175, 370))
        saveEvid.Bind(wx.EVT_BUTTON, self.OnSetEvidence)
        done = wx.Button(panel, wx.ID_CLOSE, "Done",pos=(270, 370))
        done.Bind(wx.EVT_BUTTON, self.OnCloseDone)


    #----------------------------------------------------------------------
    def widgetMaker(self, widget, objects):
        """"""
        for obj in objects:
            widget.Append(obj)
        widget.Bind(wx.EVT_COMBOBOX, self.onSelect)

    #----------------------------------------------------------------------
    def onSelect(self, event):
        """"""
        global selection, parentList       
        selection = self.cb.GetStringSelection()                    
        parentStateList=statesSave[nodesSave.index(self.cb.GetStringSelection())]
        statesEdit.SetValue(", ".join(item for item in parentStateList))
            
    def OnCloseDone(self, event):
        dlg = wx.MessageDialog(self,
             "Are you sure?",
             "Done with Evidence", wx.OK|wx.CANCEL|wx.ICON_QUESTION)
        result = dlg.ShowModal()
        dlg.Destroy()
        if result == wx.ID_OK:
            self.Close(True)
            
    def OnSetEvidence(self, event):
        global statesSave, statesEdit,probsEdit, cptsSave
        nodeData=[]
        if evidenceIn.GetValue().strip() not in statesSave[nodesSave.index(self.cb.GetStringSelection())]:
            dlg = wx.MessageDialog(self,
             "Selected state not available. Check available states - pick one.",
             "Selection Error", wx.OK|wx.ICON_QUESTION)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            #print (evidenceIn.GetValue().strip())
            #print(statesSave[nodesSave.index(self.cb.GetStringSelection())])
            evidenceNode = selection
            evidenceNodeSize = len(statesEdit.GetValue().strip().split(","))
            nodeData.append(evidenceNodeSize)
            nodeData.append(statesSave[nodesSave.index(self.cb.GetStringSelection())].index(evidenceIn.GetValue().strip()))       
            evidence={evidenceNode:nodeData}
            evidenceList.append(evidence)
            dlg = wx.MessageDialog(self,
             "Evidence confirmed for node "+selection+" (State: "+evidenceIn.GetValue().strip()+").",
             "Evidence Confirmed", wx.OK|wx.ICON_QUESTION)
            dlg.ShowModal()
            dlg.Destroy()
            nodesForEvid.remove(selection)
            self.cb.Clear()
            statesEdit.SetValue("")
            evidenceIn.SetValue("")
            self.widgetMaker(self.cb, nodesForEvid)    
            #print(evidenceList)
        #frame.Panel.bPanel.fillListCtrl()
        frame.Panel.tPanel = TopPanel(frame.Panel)
        #self.Close(True)   
         
def clearAll():
    '''clears all data'''
    nodesSave.clear()
    parentsSave.clear()
    statesSave.clear()
    cptsSave.clear()
    cpts.clear()
    evidenceList.clear()
    marginals.clear()
       
def load (filepath):
    '''Load in existing network'''
    with open(filepath) as nodes:
        nodes = json.load(nodes)
        for x in range(0,len(nodes)):
            temp1 = ''.join(nodes[x]["Parents"])
            temp2 = temp1[::-1]
            together = temp2 + nodes[x]["Name"]
            cpt = nodes[x]["cpt"]
            cpts.append(TablePotential(together,cpt))
            #append for easy saving later
            nodesSave.append(nodes[x]["Name"])
            parentsSave.append(nodes[x]["Parents"])
            statesSave.append(nodes[x]["States"])
            cptsSave.append(nodes[x]["cpt"])


class TablePotential:
    '''Subsets user-supplied conditional probability tables based on evidence set (non-evidence is set to zero)'''
    def __init__(self, dim, table, index=None):
        if (index != None):
            self.table = np.zeros(table)
            self.table[index] = 1
        else:
            self.table = np.array(table)
            self.dim = dim
        self.dim = dim

def doInference(potentials):
    '''Return probabilities given evidence set by the user'''
    #print("")
    dim = [i.dim for i in potentials]
    pots = [i.table for i in potentials]
    einsumFormat = ','.join(dim) 
    vars = sorted(list(set(''.join(dim))))
    output = [0] * len(cptsSave)
    for v in vars:
        vMarginal = np.einsum(einsumFormat+'->'+ v, *pots) 
        vMarginal = vMarginal / np.sum(vMarginal)
        #print("{} -> {}".format(v,vMarginal))
        #print(nodesSave)
        thisIndex = nodesSave.index(v)
        output[thisIndex] = vMarginal.tolist()
    
    varsString = ''.join(vars)
    joint = np.einsum(einsumFormat+'->'+varsString,*pots)
    joint = joint/np.sum(joint)
    jointString = ("{} -> {}".format(varsString, joint))
    #(output)
    #print(jointString)
    return output, jointString

def createNode():
    '''Create a node by inputting its name, parents, states, and distribution'''
    cProb = []
    name = input('Please enter name of new node (parent nodes must be created before their children): ')
    nodesSave.append(name) #add to global list
    numParents = int(input('Please enter the number of parents for new node (parent nodes must be created before children): '))
    assert isinstance (numParents, int) #assert integer
    states = []
    numStates = int(input('Please enter number of states for new node: '))
    assert isinstance(numStates, int) #assert integer
    for y in range(0,numStates):
        states.append(input('Please enter name for state ' + str(y+1) + ': '))
    statesSave.append(states) #add to global list

    if numParents > 0:
        parents = []
        for x in range(0,numParents):
            parents.append(input('Please enter name of parent ' + str(x+1) + ' in order that parent was entered: '))
        parentsCopy = copy.deepcopy(parents)
        parentsSave.append(parentsCopy)
        cProb = eval(input("Please enter conditional probability table with respect to the order that parents were entered: \n " + str(parents)))
        cptsSave.append(cProb) #add to global list
        parents.reverse() 
        parents = ''.join(parents)
        together = parents + name
    if numParents == 0: 
        cProb = eval(input("Please enter marginal probability table for node " + str(name) + ' in the form of a list: '))
        assert sum(cProb)==1, 'Marginal probabilities must add up to one.'
        cptsSave.append(cProb)
        together = name
        parentsSave.append([])
    cpt = TablePotential(together,cProb)
    cpts.append(cpt)
    return(cpt)

'''
def getUserInput():
    Allow user to set evidence for created nodes
    evidenceList=[]
    nodeData=[]    
    evidenceNum=int(input('How many nodes do you have evidence for? ' )) 
    assert isinstance(evidenceNum, int), 'Input was not recognized.'  
    for i in range(0,evidenceNum):    
        #print("")
        evidenceNode = input('Enter name of node %i: ' %(i+1))
        assert evidenceNode in nodesSave, 'Node not found.'
        evidenceNodeSize = int(input('Enter total number of states for this node: ' ))
        assert isinstance(evidenceNum, int), 'Input was not recognized.'
        nodeData.append(evidenceNodeSize)
        evidenceState = int(input('Which of these ' + '%i '%evidenceNodeSize + 'states ' +'for node %s'%evidenceNode + ' has evidence? Enter one number: ') )
        assert isinstance(evidenceNum, int), 'Input was not recognized. Must enter number.'
        nodeData.append(evidenceState)       
        evidence={evidenceNode:nodeData}
        evidenceList.append(evidence)
        nodeData=[]

    return evidenceList   
'''
     
def setEvidenceList(evidenceList):
    '''Calls table potential function for supplied evidence'''
    setEvidences=[]
    for item in evidenceList:
        for key,value in item.items():
            currentStateEvidence=TablePotential(key,value[0],value[1])        
        setEvidences.append(currentStateEvidence)
    return setEvidences

def deleteNode(node):
    cont = True
    for x in range(0,len(parentsSave)):
        if node in parentsSave[x]:
            print('This node cannot be deleted because it has child nodes that are dependent on it.\n Please delete child nodes of this node before deleting this node.')
            cont = False
    if cont == True:    
        index = nodesSave.index(node)
        del nodesSave[index]
        del parentsSave[index]
        del statesSave[index]
        del cptsSave[index]
        del cpts[index]

def save(filepath):
    with open(filepath, 'w') as outfile:
        network = []
        for z in range(0,len(nodesSave)):
            network.append({"Name": nodesSave[z],
                "Parents": parentsSave[z],
                "States": statesSave[z],
                "cpt": cptsSave[z]})
        json.dump(network, outfile)
    #del nodesSave[:]
    #del parentsSave[:]
    #del statesSave[:]
    #del cptsSave[:]
    #del cpts[:]

if __name__ == '__main__':
    app = wx.App()
    frame = DemoFrame(None, title="Bayesian Network Creator")
    frame.Show()
    app.MainLoop()
