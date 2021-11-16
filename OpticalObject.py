# -*- coding: utf-8 -*-

__title__ = 'OpticalObject'
__author__ = 'Christian Bergmann'
__license__ = 'LGPL 3.0'
__doc__ = 'Declare your FreeCAD objects to be optical mirrors, lenses or absorbers'

import os
import FreeCADGui
from FreeCADGui import doCommand, addCommand
import FreeCAD
import math

_icondir_ = os.path.join(os.path.dirname(__file__), 'icons')

INFINITY = 1677216
EPSILON = 1/INFINITY

class OpticalObjectWorker:
    def __init__(self,
                 fp,    # an instance of Part::FeaturePython
                 base = [],
                 type = 'mirror'):
        fp.addProperty('App::PropertyEnumeration', 'OpticalType', 'OpticalObject', '').OpticalType = ['mirror', 'absorber']
        fp.addProperty('App::PropertyLinkList',  'Base',   'OpticalObject',   'FreeCAD objects to be mirrors or absorbers').Base = base
        fp.OpticalType = type
        fp.Proxy = self

    def execute(self, fp):
        pass

    def onChanged(self, fp, prop):
        pass


class LensWorker:
    def __init__(self,
                 fp,    # an instance of Part::FeaturePython
                 base = [],
                 RefractionIndex = 1,
                 material = ''):
        self.update = False
        fp.addProperty('App::PropertyEnumeration', 'OpticalType', 'Lens', '').OpticalType = ['lens']
        fp.addProperty('App::PropertyLinkList',  'Base',   'Lens',   'FreeCAD objects to be lenses').Base = base
        fp.addProperty('App::PropertyFloat',  'RefractionIndex',   'Lens',   'Refractive Index at 580nm (depends on material)').RefractionIndex = RefractionIndex
        fp.addProperty(
            'App::PropertyFloatList',
            'Sellmeier',
            'Lens',
            'Sellmeier coefficients. [B1, B2, B3, C1, C2, C3]\n C1, C2, C3 in (nm)².\n Usually noted in (µm)² in literature,\n (µm)²=10⁶(nm)².')

        fp.OpticalType = 'lens'

        material_names = list(self.getMaterials())

        fp.addProperty('App::PropertyEnumeration', 'Material', 'Lens', '').Material = material_names

        self.update = True
        fp.Proxy = self

        if material in material_names:
            fp.Material = material
        else:
            fp.Material = '?'


    def getMaterials(self):
        # https://refractiveindex.info/
        return {
            '?':                 None,
            'Vacuum':            (0, 0, 0, 0, 0, 0),
            'Air':               (4.915889e-4, 5.368273e-5, -1.949567e-4, 4352.140, 17470.01, 4258444000),  #https://physics.stackexchange.com/questions/138584/sellmeier-refractive-index-of-standard-air/138617
            # 'Water':             (0, 0, 0, 0, 0, 0),  # 20°C
            # 'Ethanol':           (0, 0, 0, 0, 0, 0),
            # 'Olive oil':         (0, 0, 0, 0, 0, 0),
            # 'Ice':               (0, 0, 0, 0, 0, 0),
            'Quartz':            (0.6961663, 0.4079426, 0.8974794, 4.67914826e+03, 1.35120631e+04, 9.79340025e+07),
            'PMMA (plexiglass)': (1.1819, 0, 0, 11313, 0,  0),
            'Window glass':      (1.03961212, 0.231792344, 1.01046945, 6000.69867, 20017.9144,  103560653),
            'Polycarbonate':     (1.4182, 0, 0, 21304, 0, 0),
            # 'Flint glass':       (0, 0, 0, 0, 0, 0),
            # 'Sapphire':          (0, 0, 0, 0, 0, 0),
            # 'Cubic zirconia':    (0, 0, 0, 0, 0, 0),
            # 'Diamond':           (0, 0, 0, 0, 0, 0),
        }

    def execute(self, fp):
        pass

    def onChanged(self, fp, prop):
        if not self.update: return
        self.update = False

        if not hasattr(fp, 'Sellmeier'): return

        if prop == 'Material':
            sellmeier = self.getMaterials()[fp.Material]
            fp.Sellmeier = sellmeier
            fp.RefractionIndex = refraction_index_from_sellmeier(wavelength=580, sellmeier=fp.Sellmeier)

        if prop == 'Sellmeier':
            fp.RefractionIndex = refraction_index_from_sellmeier(wavelength=580, sellmeier=fp.Sellmeier)

        if prop == 'RefractionIndex':
            fp.Material = '?'
            fp.Sellmeier = []

        self.update = True


class TheoryLensWorker:
    def __init__(self,
                 fp,    # an instance of Part::FeaturePython
                 base = [],
                 FocalLength = 50,
                 material = ''):
        self.update = False
        fp.addProperty('App::PropertyEnumeration', 'OpticalType', 'Lens_Theory', '').OpticalType = ['lens_theory']
        fp.addProperty('App::PropertyLinkList',  'Base',   'Lens',   'FreeCAD objects to be lenses').Base = base
        fp.addProperty('App::PropertyFloat',  'FocalLength',   'Lens',   'Define F of your theoretical Lens').FocalLength = FocalLength

        fp.OpticalType = 'lens_theory'



    def execute(self, fp):
        pass

    def onChanged(self, fp, prop):
        if not self.update: return
        self.update = False


        self.update = True


class OpticalObjectViewProvider:
    def __init__(self, vobj):
        '''Set this object to the proxy object of the actual view provider'''
        vobj.Proxy = self
        self.Object = vobj.Object

    def getIcon(self):
        '''Return the icon which will appear in the tree view. This method is optional and if not defined a default icon is shown.'''
        if self.Object.OpticalType == 'mirror':
            return os.path.join(_icondir_, 'mirror.svg')

        if self.Object.OpticalType == 'absorber':
            return os.path.join(_icondir_, 'absorber.svg')

        if self.Object.OpticalType == 'lens_theory':
            return os.path.join(_icondir_, 'lens_theory.svg')

        return os.path.join(_icondir_, 'lens.svg')

    def attach(self, vobj):
        '''Setup the scene sub-graph of the view provider, this method is mandatory'''
        self.Object = vobj.Object
        self.onChanged(vobj, '')

    def updateData(self, fp, prop):
        '''If a property of the handled feature has changed we have the chance to handle this here'''
        pass

    def claimChildren(self):
        '''Return a list of objects that will be modified by this feature'''
        return self.Object.Base

    def onDelete(self, feature, subelements):
        '''Here we can do something when the feature will be deleted'''
        return True

    def onChanged(self, fp, prop):
        '''Here we can do something when a single property got changed'''
        if prop == 'Visibility':
            for vp in fp.ClaimedChildren:
                vp.Visibility = fp.Visibility

    def __getstate__(self):
        '''When saving the document this object gets stored using Python's json module.\
                Since we have some un-serializable parts here we must define this method\
                to return a tuple of all serializable objects or None.'''
        return None

    def __setstate__(self, state):
        '''When restoring the serialized object from document we have the chance to set some internals here.\
                Since no data were serialized nothing needs to be done here.'''
        return None


def refraction_index_from_sellmeier(wavelength, sellmeier):
    b1, b2, b3, c1, c2, c3 = sellmeier
    l = wavelength
    n = math.sqrt(1 + b1*l**2/(l**2 - c1) + b2*l**2/(l**2 - c2) + b3*l**2/(l**2 - c3))
    return n


class OpticalMirror():
    '''This class will be loaded when the workbench is activated in FreeCAD. You must restart FreeCAD to apply changes in this class'''

    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        doCommand('import OpticsWorkbench')
        doCommand('objects = []')
        for sel in selection:
            doCommand('objects.append(FreeCAD.ActiveDocument.getObject("%s"))'%(sel.ObjectName))

        doCommand('OpticsWorkbench.makeMirror(objects)')

    def IsActive(self):
        '''Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional.'''
        if FreeCAD.ActiveDocument:
            return(True)
        else:
            return(False)

    def GetResources(self):
        '''Return the icon which will appear in the tree view. This method is optional and if not defined a default icon is shown.'''
        return {'Pixmap'  : os.path.join(_icondir_, 'mirror.svg'),
                'Accel' : '', # a default shortcut (optional)
                'MenuText': 'Optical Mirror',
                'ToolTip' : 'Declare your FreeCAD objects to be optical mirrors' }


class OpticalAbsorber():
    '''This class will be loaded when the workbench is activated in FreeCAD. You must restart FreeCAD to apply changes in this class'''

    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        doCommand('import OpticsWorkbench')
        doCommand('objects = []')
        for sel in selection:
            doCommand('objects.append(FreeCAD.ActiveDocument.getObject("%s"))'%(sel.ObjectName))

        doCommand('OpticsWorkbench.makeAbsorber(objects)')

    def IsActive(self):
        '''Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional.'''
        if FreeCAD.ActiveDocument:
            return(True)
        else:
            return(False)

    def GetResources(self):
        '''Return the icon which will appear in the tree view. This method is optional and if not defined a default icon is shown.'''
        return {'Pixmap'  : os.path.join(_icondir_, 'absorber.svg'),
                'Accel' : '', # a default shortcut (optional)
                'MenuText': 'Optical Absorber',
                'ToolTip' : 'Declare your FreeCAD objects to be optical absorbers' }

class OpticalLens():
    '''This class will be loaded when the workbench is activated in FreeCAD. You must restart FreeCAD to apply changes in this class'''

    def Activated(self):
        selection = FreeCADGui.Selection.getSelectionEx()
        doCommand('import OpticsWorkbench')
        doCommand('objects = []')
        for sel in selection:
            doCommand('objects.append(FreeCAD.ActiveDocument.getObject("%s"))'%(sel.ObjectName))

        doCommand('OpticsWorkbench.makeLens(objects, material="Window glass")')

    def IsActive(self):
        '''Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional.'''
        if FreeCAD.ActiveDocument:
            return(True)
        else:
            return(False)

    def GetResources(self):
        '''Return the icon which will appear in the tree view. This method is optional and if not defined a default icon is shown.'''
        return {'Pixmap'  : os.path.join(_icondir_, 'lens.svg'),
                'Accel' : '', # a default shortcut (optional)
                'MenuText': 'Optical Lens',
                'ToolTip' : 'Declare your FreeCAD objects to be optical lenses' }

class TheoryLens():
    '''This class will be loaded when the workbench is activated in FreeCAD. You must restart FreeCAD to apply changes in this class'''

    def Activated(self):

        doCommand('import OpticsWorkbench')
        doCommand('objects = []')
        doCommand('App.ActiveDocument.addObject("Part::Cylinder","Disk")')
        doCommand('App.ActiveDocument.ActiveObject.Label = "Disk"')
        doCommand('App.ActiveDocument.recompute()')
        doCommand('Gui.SendMsgToActiveView("ViewFit")')
        doCommand('doc = FreeCAD.ActiveDocument.Name')
        doCommand('FreeCAD.getDocument(doc).getObject("Disk").Radius = "20.0000 mm"')
        doCommand('FreeCAD.getDocument(doc).getObject("Disk").Height = "0.0010 mm"')
        doCommand('Gui.Selection.addSelection(doc,"Disk")')
        selection = FreeCADGui.Selection.getSelectionEx()
        for sel in selection:
            doCommand('objects.append(FreeCAD.ActiveDocument.getObject("%s"))'%(sel.ObjectName))

        #doCommand('OpticsWorkbench.makeLens(objects, material="Window glass")')
        doCommand('print("test OK OK")')
        doCommand('OpticsWorkbench.make_theory_Lens(objects, focallength=60)')

    def IsActive(self):
        '''Here you can define if the command must be active or not (greyed) if certain conditions
        are met or not. This function is optional.'''
        if FreeCAD.ActiveDocument:
            return(True)
        else:
            return(False)

    def GetResources(self):
        '''Return the icon which will appear in the tree view. This method is optional and if not defined a default icon is shown.'''
        return {'Pixmap'  : os.path.join(_icondir_, 'lens_theory.svg'),
                'Accel' : '', # a default shortcut (optional)
                'MenuText': 'Theoretical Optical Lens',
                'ToolTip' : 'Create a FreeCAD objects being theoretical optical lense' }

addCommand('Mirror', OpticalMirror())
addCommand('Absorber', OpticalAbsorber())
addCommand('Lens', OpticalLens())
addCommand('Lens_Theory', TheoryLens())
