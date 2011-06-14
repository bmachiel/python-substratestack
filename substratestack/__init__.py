# Copyright (c) 2011 Brecht Machiels <brecht.machiels@esat.kuleuven.be>
#                    ESAT-MICAS, K.U.Leuven
#
# This file is part of python-substratestack
# (http://github.com/bmachiel/python-substratestack).
#
# python-substratestack is free software: you can redistribute it and/or modify
# it under the terms of the BSD (2-clause) license.
#
# python-substratestack is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the included LICENSE
# file for details.

"""python-substratestack

substratestack is a Python module that helps simplify substrate stackups and
export them for use in Momentum and Sonnet.
"""

from __future__ import division

from pyx import *
from pyx import bbox

import re
from copy import copy


## TODO: does the (Momentum) expansion of the metals (up or down) correspond to
##       the way oxides are merged?

## TODO: generate layer mapping file for Sonnet GDS import


progname = __file__
try:
    from version import __version__
except ImportError:
    __version__ = 'unknown (package not built using setuptools)'
progrevision = __version__


m = 1 # m                       1 meter
mm = 1e-3 # m                   1 millimeter
um = 1e-6 # m                   1 micrometer
A = 1e-10 # m                   1 Angstrom
kA = 1e3 * A # m                1 kiloAngstrom
Ohm_m = 1 # Ohm*m
Ohm_cm = 1e-2 # Ohm*m
S_m = 1 # S/m
Ohm_sq = 1 # Ohm/sq             sheet resistance
mOhm_sq = 1e-3 # Ohm/sq         sheet resistance
Ohm = 1 # Ohm
mOhm = 1e-3 # Ohm


paper = document.paperformat.A4
unit.set(defaultunit="mm")
text.set(mode="latex")
text.preamble(r"\usepackage{times}")
text.preamble(r"\usepackage{amssymb}")
text.preamble(r"\parindent=0pt")


class SubstrateLayer:
    """Class representing a layer in a substrate stack"""
    def __init__(self, thickness, epsilon_rel, loss_tangent=0):
        """Create a new substrate layer with a given thickness, relative 
        permittivity and loss tangent.
        
        """
        self.thickness = thickness
        self.epsilon_rel = epsilon_rel
        self.loss_tangent = loss_tangent
        self.top_interface = None
        self.bottom_interface = None


class BulkLayer(SubstrateLayer):
    """Class representing a bulk layer, the base layer in a substrate stack"""
    def __init__(self, thickness, epsilon_rel, resistivity, loss_tangent=0):
        """Create a new bulk layer with a given thickness, relative 
        permittivity, resistivity and loss tangent.
        
        """
        SubstrateLayer.__init__(self, thickness, epsilon_rel, loss_tangent)
        self.resistivity = resistivity


class OxideLayer(SubstrateLayer):
    """Class representing an oxide layer"""
    def __init__(self, thickness, epsilon_rel, loss_tangent=0):
        """Create a new oxide layer with a given thickness, relative 
        permittivity, and loss tangent.
        
        """
        SubstrateLayer.__init__(self, thickness, epsilon_rel, loss_tangent)


class Interface:
    """Class representing an interface between two substrate layers"""
    def __init__(self, bottom_layer, top_layer=None):
        """Define a new interface between a bottom layer and a top layer"""
        assert isinstance(bottom_layer, SubstrateLayer)
        if top_layer:
            assert isinstance(top_layer, SubstrateLayer)
        self.bottom_layer = bottom_layer
        self.top_layer = top_layer
        self.metal = None
        

class MetalLayer:
    """Class representing a metal layer"""
    def __init__(self, name, thickness, sheet_resistance, extend_direction):
        """Define a new metal with a given name, thickness, relative
        permittivity, sheet resistance. and extension direction.
        
        """
        assert extend_direction in (UP, DOWN)
        self.name = name
        self.thickness = thickness
        self.sheet_resistance = sheet_resistance
        self.extend_direction = extend_direction
        self.top_interface = None
        self.bottom_interface = None

    def __repr__(self):
        """Return a textual representation of the metal"""
        upordown = 'up' if self.extend_direction > 0 else 'down'
        return self.name + " (" + upordown + ")"

    def get_resistivity(self):
        """Return the resistivity of the metal"""
        return self.sheet_resistance * self.thickness
        
    def get_conductivity(self):
        """Return the conductivity of the metal"""
        return 1.0 / self.get_resistivity()


class Via:
    """Class representing a via connecting two metal layers"""
    def __init__(self, name, resistance, width, spacing=0):
        """Define a new via with a given name, resistance and width. Optionally
        one can specify a via spacing. This will make the via represent an
        equivalent resistivity.
        
        """
        self.name = name
        self.resistance = resistance
        self.width = width
        self.spacing = spacing
        self.top_metal = None
        self.bottom_metal = None
        self._stack = None

    @property
    def fill(self):
        """Return the fill percentage of the via. This is defined as the total
        effective via area to the total via farm area.
        
        """
        return self.width**2 / ((self.width + self.spacing)**2)

    def get_height(self):
        """Return the height of the via"""
        return self._stack.get_via_height(self)
        
    def get_resistivity(self):
        """Return the resistivity of the via"""
        return self.resistance * self.width**2 / self.get_height() / self.fill
        
    def get_conductivity(self):
        """Return the conductivity of the via"""
        return 1.0 / self.get_resistivity()


# metal layer extend directions
DOWN = -1
UP = +1


class SubstrateStack:
    """Class representing a substrate stack made up of a bulk layer,
    oxide layers, metal layers and via's.
    
    """
    def __init__(self, bulk_layer):
        """Create a new substrate with bulk_layer as the base"""
        print("WARNING: this software comes without any warranty. ")
        print("Any output this application generates may or may not be \n" +
           "correct. Be sure to always verify it manually.")
        assert isinstance(bulk_layer, BulkLayer)
        self.oxide_layers = []
        self.interfaces = []
        self.metal_layers = []
        self.vias = []
        self.bulk_layer = bulk_layer
        first_interface = Interface(self.bulk_layer)
        first_interface.bottom_layer = self.bulk_layer
        self.bulk_layer.top_interface = first_interface        
        self.interfaces.append(first_interface)

    def add_oxide_layer_on_top(self, oxide_layer):
        """Add oxide_layer to the top of the substrate stack"""
        assert isinstance(oxide_layer, OxideLayer)
        bottom_interface = self.interfaces[-1]
        bottom_interface.top_layer = oxide_layer
        oxide_layer.bottom_interface = bottom_interface
        top_interface = Interface(oxide_layer)
        self.interfaces.append(top_interface)
        oxide_layer.top_interface = top_interface
        self.oxide_layers.append(oxide_layer)

    def add_metal_layer(self, metal_layer, interface_number):
        """Add metal_layer at the interface specified by interface_number"""
        assert isinstance(metal_layer, MetalLayer)
        self.metal_layers.append(metal_layer)
        interface = self.interfaces[interface_number]
        interface.metal = metal_layer
        if metal_layer.extend_direction == DOWN:
            metal_layer.top_interface = interface
        else:
            metal_layer.bottom_interface = interface

    def get_metal_layer_by_name(self, name):
        """Return the metal layer based on its name"""
        for metal_layer in self.metal_layers:
            if metal_layer.name == name:
                return metal_layer
            
        return None

    def add_via(self, via, metal1_name, metal2_name):
        """Add a via between two metals, specified by their name"""
        assert isinstance(via, Via)
        metal1 = self.get_metal_layer_by_name(metal1_name)
        metal2 = self.get_metal_layer_by_name(metal2_name)
        assert metal1 and metal2
        self.vias.append(via)
        metal1_interface = metal1.bottom_interface or metal1.top_interface
        metal2_interface = metal2.bottom_interface or metal2.top_interface
        if self.get_interface_position(metal1_interface) > \
           self.get_interface_position(metal2_interface):
            via.top_metal = metal1
            metal1.bottom_via = via
            via.bottom_metal = metal2
            metal2.top_via = via
        else:
            via.top_metal = metal2
            metal2.bottom_via = via
            via.bottom_metal = metal1
            metal2.top_via = via
        via._stack = self

    def get_via_by_top_metal(self, top_metal):
        """Return top_metal's lower via"""
        for via in self.vias:
            if via.top_metal == top_metal:
                return via
            
        return None

    def get_via_by_bottom_metal(self, bottom_metal):
        """Return bottom_metal's upper via"""
        for via in self.vias:
            if via.bottom_metal == bottom_metal:
                return via
            
        return None

    def get_interface_number(self, interface):
        """Return interface's index"""
        return self.interfaces.index(interface)

    def get_interface_position(self, interface):
        """Return interface's absolute position (in meters) in the substrate
        stack, where the top of the bulk layer is 0 m"""
        position = - self.bulk_layer.thickness        # exclude bulk thickness
        for itf in self.interfaces:
            position += itf.bottom_layer.thickness
            if interface == itf:
                return position
        
    def get_via_height(self, via):
        """Return via's height in meters"""
        if via.bottom_metal.extend_direction == UP:
            top_of_bottom_metal = self.get_interface_position(
               via.bottom_metal.bottom_interface)
            top_of_bottom_metal += via.bottom_metal.thickness
        else:
            top_of_bottom_metal = self.get_interface_position(
               via.bottom_metal.top_interface)
        
        if via.top_metal.extend_direction == DOWN:
            bottom_of_top_metal = self.get_interface_position(
               via.top_metal.top_interface)
            bottom_of_top_metal -= via.top_metal.thickness
        else:
            bottom_of_top_metal = self.get_interface_position(
               via.top_metal.bottom_interface)
        
        return bottom_of_top_metal - top_of_bottom_metal

    def get_stack_height(self):
        """Return the total height of the stack in meters"""
        height = 0
        for oxide_layer in self.oxide_layers:
            height += oxide_layer.thickness
            
        return height
    
    def split_oxide_layer(self, position):
        """Split the stack's oxide layers at the given absolute position"""
        new_interface = None
        for i, oxide_layer in enumerate(self.oxide_layers):
            oxide_top = self.get_interface_position(oxide_layer.top_interface)
            oxide_bottom = self.get_interface_position(
               oxide_layer.bottom_interface)
            if oxide_top > position and position > oxide_bottom:
                oxide_layer.thickness = position - oxide_bottom
                new_oxide_layer = OxideLayer(oxide_top - position,
                                             oxide_layer.epsilon_rel,
                                             oxide_layer.loss_tangent)
                new_interface = Interface(oxide_layer, new_oxide_layer)
                self.interfaces.insert(
                   self.get_interface_number(oxide_layer.top_interface),
                   new_interface)
                new_oxide_layer.bottom_interface = new_interface
                new_oxide_layer.top_interface = oxide_layer.top_interface
                oxide_layer.top_interface.bottom_layer = new_oxide_layer
                oxide_layer.top_interface = new_interface
                self.oxide_layers.insert(i + 1, new_oxide_layer)

        return new_interface

    def get_interface_by_position(self, position):
        """Return the interface at the given absolute position"""
        float_threshold = 1e-15
        for interface in self.interfaces:
            if abs(self.get_interface_position(interface) - position) < \
               float_threshold:
                return interface
        return None

    def is_standard(self):
        """Check whether the stack is in standard format"""
        for metal_layer in self.metal_layers:
            if not (metal_layer.top_interface and metal_layer.bottom_interface):
                return False
            if metal_layer.extend_direction != UP:
                return False
        
        return True

    def standardize(self):
        """Transform this substrate stack such that:
        * there are oxide interfaces at both boundaries of all metals
        * all metals extend up
        
        """
        # create interfaces at boundaries of the metals
        for metal_layer in self.metal_layers:
            # metal extends down
            if metal_layer.top_interface and not metal_layer.bottom_interface:
                top_position = \
                   self.get_interface_position(metal_layer.top_interface)
                bottom_position = top_position - metal_layer.thickness
                bottom_interface = \
                   self.get_interface_by_position(bottom_position)
                if bottom_interface:
                    metal_layer.bottom_interface = bottom_interface
                else:
                    metal_layer.bottom_interface = \
                       self.split_oxide_layer(bottom_position)
            # metal extends up
            elif metal_layer.bottom_interface and \
               not metal_layer.top_interface:
                bottom_position = \
                   self.get_interface_position(metal_layer.bottom_interface)
                top_position = bottom_position + metal_layer.thickness
                top_interface = self.get_interface_by_position(top_position)
                if top_interface:
                    metal_layer.top_interface = top_interface
                else:
                    metal_layer.top_interface = \
                       self.split_oxide_layer(top_position)
                    
        # make all metals extend up
        for metal_layer in self.metal_layers:
            if metal_layer.extend_direction == DOWN:
                metal_layer.top_interface.metal = None
                metal_layer.bottom_interface.metal = metal_layer
                metal_layer.extend_direction = UP

    def merge_oxide_layers(self, oxide_layers):
        """Merge the given oxide layers into one equivalent layer. oxide layers
        is a list sorted from bottom to top.
        
        """
        assert len(oxide_layers) > 1
        top_interface = oxide_layers[-1].top_interface
        oxide_layer = oxide_layers[0]
        bottom_interface = oxide_layer.bottom_interface
        total_thickness = oxide_layer.thickness
        total_epsilon_rel = oxide_layer.thickness / oxide_layer.epsilon_rel
        total_loss_tangent = oxide_layer.thickness * oxide_layer.loss_tangent
        insert_position = self.oxide_layers.index(oxide_layer)
        for i, oxide_layer in enumerate(oxide_layers[1:]):
            # the given oxide layer list should be sorted from bottom to top
            assert oxide_layer.bottom_interface == \
               oxide_layers[i].top_interface
            # there should be no metal attached to the interfaces to be removed
            assert oxide_layer.bottom_interface.metal == None
            
            total_thickness += oxide_layer.thickness
            total_epsilon_rel += (oxide_layer.thickness /
                                  oxide_layer.epsilon_rel)
            total_loss_tangent += (oxide_layer.thickness *
                                   oxide_layer.loss_tangent)
            
            self.interfaces.remove(oxide_layer.bottom_interface)
            self.oxide_layers.remove(oxide_layer)
        
        self.oxide_layers.remove(oxide_layers[0])        
        merged_oxide_layer = OxideLayer(total_thickness,
                                        total_thickness / total_epsilon_rel,
                                        total_loss_tangent / total_thickness)
        merged_oxide_layer.top_interface = top_interface
        merged_oxide_layer.bottom_interface = bottom_interface
        top_interface.bottom_layer = merged_oxide_layer
        bottom_interface.top_layer = merged_oxide_layer
        self.oxide_layers.insert(insert_position, merged_oxide_layer)
    
    def remove_metal_layer_by_name(self, metal_layer_name):
        """Remove the metal as specified by metal_layer_name from the stack"""
        metal_layer = self.get_metal_layer_by_name(metal_layer_name)
        if  metal_layer.top_interface:
            metal_layer.top_interface.metal = None
        if metal_layer.bottom_interface:
            metal_layer.bottom_interface.metal = None
        if self.get_via_by_top_metal(metal_layer):
            via = self.get_via_by_top_metal(metal_layer)
            self.vias.remove(via)
        if self.get_via_by_bottom_metal(metal_layer):
            via = self.get_via_by_bottom_metal(metal_layer)
            self.vias.remove(via)
        self.metal_layers.remove(metal_layer)

    def simplify(self):
        """Simplify the oxide stack such that there are no more interfaces than
        necessary (for attaching metal layers to).
        
        """
        if not self.is_standard():
            self.standardize()
        bottom_oxide_layer_index = \
           self.oxide_layers.index(self.bulk_layer.top_interface.top_layer)
        for metal_layer in self.metal_layers:
            if isinstance(metal_layer.bottom_interface.bottom_layer,
                          BulkLayer):
                continue
            top_oxide_layer_index = self.oxide_layers.index(
               metal_layer.bottom_interface.bottom_layer)
            self.merge_oxide_layers(self.oxide_layers
               [bottom_oxide_layer_index:top_oxide_layer_index + 1])
            bottom_oxide_layer_index = \
               self.oxide_layers.index(metal_layer.bottom_interface.top_layer)
            
        top_oxide_layer_index = \
           self.oxide_layers.index(self.interfaces[-1].bottom_layer)
        self.merge_oxide_layers(self.oxide_layers
           [bottom_oxide_layer_index:top_oxide_layer_index + 1])

    def simplify2(self):
        if not self.is_standard():
            self.standardize()
        bottom_oxide_layer_index = \
           self.oxide_layers.index(self.bulk_layer.top_interface.top_layer)
        for metal_layer in self.metal_layers:
            top_oxide_layer_index = self.oxide_layers.index(
               metal_layer.bottom_interface.bottom_layer)
            print metal_layer.name, '**', \
               self.interfaces.index(metal_layer.bottom_interface), \
               '<<', self.interfaces.index(metal_layer.top_interface)
            print bottom_oxide_layer_index, '<', top_oxide_layer_index
            self.merge_oxide_layers(self.oxide_layers
               [bottom_oxide_layer_index:top_oxide_layer_index + 1])
            bottom_oxide_layer_index = \
               self.oxide_layers.index(metal_layer.bottom_interface.top_layer)
            top_oxide_layer_index = \
               self.oxide_layers.index(metal_layer.top_interface.bottom_layer)
            print bottom_oxide_layer_index, '<', top_oxide_layer_index
            self.merge_oxide_layers(self.oxide_layers
               [bottom_oxide_layer_index:top_oxide_layer_index + 1])
            bottom_oxide_layer_index = \
               self.oxide_layers.index(metal_layer.top_interface.top_layer)
            
        top_oxide_layer_index = \
           self.oxide_layers.index(self.interfaces[-1].bottom_layer)
        self.merge_oxide_layers(self.oxide_layers
           [bottom_oxide_layer_index:top_oxide_layer_index + 1])

    def write_momentum_substrate(self, filename, infinite_ground_plane=False):
        """Write out the substrate definition as an ADS Momentum substrate
        file
        
        """
        last_metal_above = 1
        last_via_inside = 0
        f = open(filename + '.slm', 'w')
        assert f
        if not self.is_standard():
            self.standardize()
        y = self.bulk_layer.thickness + self.get_stack_height()
        for met in self.metal_layers:
            y -= met.thickness
        text = []
        text.append("VERSION 100")
        text.append("UNIT um")
        text.append("SUBNAME")
        text.append("TOP 0 0 0 0")
        if infinite_ground_plane:
            text.append("BOTTOM 1 1 0 0")
        else:
            text.append("BOTTOM 1 0 0 0")
        text.append("SUB0 TOP 1 1 0 0 1 0 -1 %g %g 1 0 3" % (y, y))
        self.oxide_layers.reverse()
        metal_text = []
        metal_number = 1
        for i, oxide_layer in enumerate(self.oxide_layers):
            metal = oxide_layer.bottom_interface.metal
            if metal:
                assert metal.extend_direction == UP
                thickness = - metal.thickness
                metal_above = 2
                via = self.get_via_by_top_metal(metal)
                sigma = metal.get_conductivity()
                metal_text.append(
                   "MET%s %s %s 1 2 3 %s 0 Siemens/m Siemens/m 1 %s um" %
                   (str(metal_number).ljust(3), metal.name.ljust(10),
                    str(y - (oxide_layer.thickness -
                             metal.thickness)).ljust(12),
                    str(sigma).ljust(16),
                    str(metal.thickness / um).ljust(6)))
                metal_number += 1
                if via:
                    via_inside = 1
                    sigma = via.get_conductivity()
                    metal_text.append(
                       "MET%s %s %s 0 4 3 %s 0 Siemens/m Siemens/m 0 %s um" %
                       (str(metal_number).ljust(3), via.name.ljust(10),
                        str(y - (oxide_layer.thickness -
                                 metal.thickness)).ljust(12),
                        str(sigma).ljust(16),
                        str(0).ljust(6)))
                    metal_number += 1
                else:
                    via_inside = 0
            else:
                thickness = 0
                metal_above = 1
                via_inside = 0

            thickness += oxide_layer.thickness
            text.append("SUB%d ox%d 1 %g %g 0 1 0 %g %g %g %d %d 3" % 
               (i + 1, len(self.oxide_layers) - i, oxide_layer.epsilon_rel,
                oxide_layer.loss_tangent, thickness / um, y - thickness, y,
                last_metal_above, last_via_inside))
            y -= thickness

            last_metal_above = metal_above
            last_via_inside = via_inside

        text.append("SUB%d bulk 2 %g %g 0 1 0 %g %g %g %d 0 3" %
           (len(self.oxide_layers) + 1, self.bulk_layer.epsilon_rel,
            1/self.bulk_layer.resistivity, self.bulk_layer.thickness / um, 0,
            y, last_metal_above))
        if not infinite_ground_plane:
            text.append("SUB%d AIR 1 1 0 0 1 0 -1 0 0 1 0 3" % 
                        (len(self.oxide_layers) + 2))
        
        text += metal_text

        f.write('\n'.join(text))
        f.close()
        self.oxide_layers.reverse()  # restore the order of oxide layers

    def write_sonnet_technology(self, filename):
        """Write out the substrate definition as a Sonnet technology file"""
        from datetime import datetime
        now = datetime.now()
        f = open(filename + '.son', 'w')
        assert f
        if not self.is_standard():
            self.standardize()
        text = []
        text.append("FTYP SONPROJ 3 ! Sonnet Project File")
        text.append("VER 11.56")
        text.append("HEADER")
        text.append("DAT %s" % now.strftime("%m/%d/%Y %H:%M:%S"))
        text.append("BUILT_BY_CREATED %s r%s %s" %
           (progname, progrevision, now.strftime("%m/%d/%Y  %H:%M:%S")))
        text.append("BUILT_BY_SAVED %s r%s" % (progname, progrevision))
        text.append("MDATE %s" % now.strftime("%m/%d/%Y  %H:%M:%S"))
        text.append("HDATE %s" % now.strftime("%m/%d/%Y  %H:%M:%S"))
        text.append("END HEADER")
        text.append("DIM")
        text.append("FREQ GHZ")
        text.append("IND PH")
        text.append("LNG UM")
        text.append("ANG DEG")
        text.append("CON /OH")
        text.append("CAP PF")
        text.append("RES OH")
        text.append("END DIM")
        text.append("GEO")
        text.append('TMET "Lossless" 0 SUP 0 0 0 0')
        text.append('BMET "Lossless" 0 SUP 0 0 0 0')

        self.oxide_layers.reverse()
        metal_index = 0  # TODO: this is more than just an index
        for metal in self.metal_layers:
            metal_index += 1
            sigma = metal.get_conductivity()
            text.append('MET "%s" %d TMM %d 0 %g' % (metal.name, metal_index,
                                                     sigma,
                                                     metal.thickness / um))

        for via in self.vias:
            metal_index += 1
            sigma = via.get_conductivity()
            height = self.get_via_height(via)
            text.append('MET "%s" %d NOR %d 0 %g' % (via.name, metal_index,
                                                     sigma, height / um))

        text.append("BOX %d 4064 4064 32 32 20 0" % (len(self.oxide_layers) +
                                                     1))
        # air layer
        text.append('      %g %g 1 %g 0 %g 0 "%s"' %
           (500, 1.0, 0.0, 0.0, "air"))
        for i, oxide_layer in enumerate(self.oxide_layers):
            thickness = oxide_layer.thickness / um
            if thickness == 0:
                thickness = 1e-9
            text.append('      %g %g 1 %g 0 0 0 "%s"' % (thickness,
               oxide_layer.epsilon_rel, oxide_layer.loss_tangent, "oxide"))

        bulk = self.bulk_layer
        text.append('      %g %g 1 %g 0 %g 0 "%s"' % (bulk.thickness / um,
                                                      bulk.epsilon_rel,
                                                      bulk.loss_tangent,
                                                      1.0 / bulk.resistivity,
                                                      "bulk"))
        
        text.append("NUM 0")
        text.append("END GEO")

        f.write('\n'.join(text))
        f.close()
        self.oxide_layers.reverse()

    def draw(self, filename, pages=3, single_page=True):
        """Render a representation of the stack to a PDF file.
        
        filename:    should not include the pdf extension
        pages:       indicates the number of pages the stack should be tall
        single_page: render a single tall page or split up the stack
        
        """
        # positions for labels and boxes
        x1 = 0
        x2 = 160
        x_space = 2
        x_thickness = 95
        x_eps = 135
        x_interface_number = 7
        x_interface_number2 = 15
        x_metal_offset = 15
        x_metal_width = 60
        x_via_width = 40
        
        stack_height = self.get_stack_height()
        top_interface = self.oxide_layers[-1].top_interface
        total_interfaces = self.get_interface_number(top_interface)
        canvas_height = 0.95 * pages * unit.tomm(paper.height)
        factor = canvas_height / stack_height
        escape = ('_', )
        canvas_pages = []
        c = canvas.canvas()
        y = 0
        for oxide_layer in self.oxide_layers:
            bottom_interface = oxide_layer.bottom_interface
            oxide_thickness_in_mm = oxide_layer.thickness * factor
            fill_color = color.grey(1.0 - oxide_layer.epsilon_rel/20.0)
            #c.stroke(path.line(x1, y, x2, y), [style.linewidth(0.3)])
            c.stroke(path.rect(x1, y, x2 - x1, oxide_thickness_in_mm),
                [style.linewidth(0.3), deco.filled([fill_color])])
            c.text(x_thickness, y + oxide_thickness_in_mm / 2.0,
                   r'$d = %g \mu m~(%g kA)$' % (oxide_layer.thickness / um,
                                                oxide_layer.thickness / kA),
                   [text.halign.left, text.valign.middle])
            c.text(x_eps, y + oxide_thickness_in_mm / 2.0,
                   '$\epsilon_r = %g$' % (oxide_layer.epsilon_rel),
                   [text.halign.left, text.valign.middle])

            # interface numbers
            number = self.get_interface_number(bottom_interface)
            c.text(x1 - x_interface_number - x_space, y,
                   '$%d$' % (number),
                   [text.halign.right, text.valign.middle])
            c.text(x1 - x_interface_number2 - x_space, y,
                   '$%d$' % (total_interfaces - number),
                   [text.halign.right, text.valign.middle])
            c.stroke(path.line(x1 - x_interface_number, y, x1, y),
                     [style.linewidth(0.3), deco.earrow()])

            # interface position
            c.stroke(path.line(x2, y, x2 + x_interface_number / 2.0, y),
                     [style.linewidth(0.3)])
            c.text(x2 + x_interface_number/2.0 + x_space, y,
                   '$%g \mu m$' %
                      (self.get_interface_position(bottom_interface) / um),
                   [text.halign.left, text.valign.middle])

            y += oxide_thickness_in_mm

        top_interface = oxide_layer.top_interface
        # last interface number
        c.text(x1-x_interface_number-x_space, y,
               '$%d$' % (self.get_interface_number(top_interface)),
               [text.halign.right, text.valign.middle])
        c.text(x1 - x_interface_number2 - x_space, y,
               '$%d$' % (0),
               [text.halign.right, text.valign.middle])
        c.stroke(path.line(x1 - x_interface_number, y, x1, y),
                 [style.linewidth(0.3), deco.earrow()])

        # last interface position
        c.stroke(path.line(x2, y, x2 + x_interface_number/2.0, y),
                 [style.linewidth(0.3)])
        c.text(x2 + x_interface_number/2.0 + x_space, y,
               '$%g \mu m$' %
                  (self.get_interface_position(top_interface) / um),
               [text.halign.left, text.valign.middle])

        canvas_pages.append(c)

        # draw metals
        document_pages = []
        current_page = 0
        c = canvas_pages[current_page]
        y = 0
        metal_color = color.rgb(0.5, 0.8, 1.0)
        via_color = color.rgb(0.8, 0.8, 1.0)
        for oxide_layer in self.oxide_layers:
            bottom_interface = oxide_layer.bottom_interface
            oxide_thickness_in_mm = oxide_layer.thickness * factor
            # metal
            if bottom_interface.metal:
                metal_layer = bottom_interface.metal
                extend_direction = metal_layer.extend_direction
                metal_thickness_in_mm = metal_layer.thickness * factor
                c.stroke(path.rect(x1 + x_metal_offset, y, x_metal_width,
                         extend_direction * metal_thickness_in_mm),
                         [style.linewidth(0.3), deco.filled([metal_color])])
                center = (x1 + x_metal_offset + x_metal_width / 2.0,
                          y + extend_direction * metal_thickness_in_mm / 2.0)
                sigma = metal_layer.get_conductivity()
                name = metal_layer.name
                for char in escape:
                    name = name.replace(char, '\\' + char)
                metal_text = (r'\begin{center}{\bf %s}\\' % (name) +
                              r'$d = %g \mu m~(%g kA)$\\' %
                                 (metal_layer.thickness / um,
                                  metal_layer.thickness / kA) +
                              r'$\sigma = %.3g S/m$\\' % (sigma)+
                              r'$R_{sheet} = %g m\Omega/\square$\end{center}' %
                                (metal_layer.sheet_resistance / mOhm_sq))
                c.text(center[0], center[1], metal_text, 
                       [text.parbox(x_metal_width), text.valign.middle,
                        text.halign.boxcenter])
                
                # via
                if self.get_via_by_bottom_metal(metal_layer):
                    via = self.get_via_by_bottom_metal(metal_layer)
                    via_height = self.get_via_height(via) * factor
                    y_top_of_metal = \
                       max(y, y + extend_direction * metal_thickness_in_mm)
                    c.stroke(path.rect(x1 + x_metal_offset +
                                (x_metal_width - x_via_width) / 2.0,
                             y_top_of_metal, x_via_width, via_height),
                             [style.linewidth(0.3), deco.filled([via_color])])
                    if extend_direction == UP:
                        y_extra = metal_layer.thickness * factor
                    else:
                        y_extra = 0
                    center = (x1 + x_metal_offset + x_metal_width / 2.0,
                              y + via_height / 2.0 + y_extra)
                    sigma = via.get_conductivity()
                    name = via.name
                    for char in escape:
                        name = name.replace(char, '\\' + char)
                    via_text = (r'\begin{center}{\bf %s}\\' % (name) +
                                r'$h = %g \mu m~(%g kA)$\\' %
                                 (via.get_height() / um,
                                  via.get_height() / kA) +
                                r'$\sigma_{eq} = %.3g S/m$\\' % (sigma) +
                                r'$R = %g\Omega$\\' % (via.resistance) +
                                r'via fill = %g \%%\end{center}' %
                                   (via.fill * 100))
                    c.text(center[0], center[1], via_text,
                           [text.parbox(x_via_width), text.valign.middle,
                            text.halign.boxcenter])

            y += oxide_thickness_in_mm

        c.stroke(path.line(x1, y, x2, y), [style.linewidth(0.3)])

        if single_page:
            tall_paper = copy(paper)
            tall_paper.height = pages * paper.height
            document_pages.append(document.page(c, None,
                                                paperformat=tall_paper))
        else:
            for i in range(3):
                bounding_box = \
                   bbox.bbox(x1, i * 0.95 * unit.tomm(paper.height), x2,
                             (i + 1) * 0.95 * unit.tomm(paper.height))
                document_pages.append(document.page(c, None, paper,
                                                    bbox=bounding_box))

        doc = document.document(document_pages)

        #doc.writePSfile(filename + '.ps')
        doc.writePDFfile(filename + '.pdf')
