#!/bin/env python

# This file serves as an example for the substratestack Python module. It
# describes a hypothetical six metal layer CMOS substrate stack with an
# optional thick top metal

# Arguments are specified as follows: <number> * <unit>, where unit is one of
# following list. When no unit is specified, the default is used.
#
# for thickness:
#  * m (meter) [default]
#  * mm (millimeter)
#  * um (micrometer)
#  * A (Angstrom)
#  * kA (kiloAngstrom)
#
# for resistivity:
#  * Ohm_m (Ohm * m) [default]
#  * Ohm_cm (Ohm * cm)
#
# for conductivity:
#  * S_m (Siemens/meter) [default]
#
# for resistance:
#  * Ohm (Ohm) [default]
#  * mOhm (milliOhm)
#
# for sheet resistance:
#  * Ohm_sq (Ohm / square) [default]
#  * mOhm_sq (milliOhm / square)


# import everything needed from the substratestack module
from substratestack import m, mm, um, A, kA
from substratestack import Ohm_m, Ohm_cm, S_m, Ohm, mOhm, Ohm_sq, mOhm_sq

from substratestack import SubstrateStack
from substratestack import BulkLayer, OxideLayer, MetalLayer, Via, UP, DOWN

# set to true to use the thick top metal option
thick_top_metal = False

# loss tangent value to use in oxide layer definitions
loss_tangent = 0
# NOTE: setting a non-zero loss tangent can cause some problems with Momentum

# The stack is entered from bottom to top, starting with the bulk.
# BulkLayer arguments: thickness, resistivity, dielectric loss tangent
bulk = BulkLayer(300 * um, 11.9, 20 * Ohm_cm, loss_tangent)
# NOTE: 
#  Sonnet uses dielectric loss tangent AND resistivity
#  Momentum uses only resistivity

# Create a SubstrateStack object using the specified bulk layer.
stack = SubstrateStack(bulk)

# Add all oxide layers to the stack, starting with the bottom one, working
# up to the top.
# OxideLayer arguments: thickness, relative epsilon, loss tangent
stack.add_oxide_layer_on_top(OxideLayer(300 * A, 7, loss_tangent))
stack.add_oxide_layer_on_top(OxideLayer(5.0 * kA, 4, loss_tangent))
stack.add_oxide_layer_on_top(OxideLayer(300 * A, 4.1, loss_tangent))

# The following oxide layers repeat four times
for i in range(4):
    stack.add_oxide_layer_on_top(OxideLayer(5.0 * kA, 3.7, loss_tangent))
    stack.add_oxide_layer_on_top(OxideLayer(300 * A, 4.1, loss_tangent))

# The thickness of the following layers depend on the thick metal option
if thick_top_metal:
    stack.add_oxide_layer_on_top(OxideLayer(30 * kA, 3.7, loss_tangent))
    stack.add_oxide_layer_on_top(OxideLayer(500 * A, 4.1, loss_tangent))
else:
    stack.add_oxide_layer_on_top(OxideLayer(10 * kA, 3.7, loss_tangent))
    stack.add_oxide_layer_on_top(OxideLayer(500 * A, 4.1, loss_tangent))

# Add passivation layers
stack.add_oxide_layer_on_top(OxideLayer(4*kA, 7, loss_tangent))

if __name__ == '__main__':
    # Print the layer stack to example_nometals.pdf to see the numbering of the
    # interfaces between oxide layers.
    # draw arguments: filename (without extension), number of pages to stretch 
    #   the substrate across, create one tall page instead of splitting the stack
    stack.draw('example_nometals', pages=3, single_page=True)

# Add metal layers
# MetalLayer arguments: name, thickness, sheet resistance, extension direction,
#   interface number
stack.add_metal_layer(MetalLayer('PO1', 1.5 * kA, 10 * Ohm_sq, UP), 0)
stack.add_metal_layer(MetalLayer('ME1', 2.0 * kA, 120 * mOhm_sq, DOWN), 2)
stack.add_metal_layer(MetalLayer('ME2', 3.0 * kA, 100 * mOhm_sq, DOWN), 4)
stack.add_metal_layer(MetalLayer('ME3', 3.0 * kA, 100 * mOhm_sq, DOWN), 6)
stack.add_metal_layer(MetalLayer('ME4', 3.0 * kA, 100 * mOhm_sq, DOWN), 8)
stack.add_metal_layer(MetalLayer('ME5', 3.0 * kA, 100 * mOhm_sq, DOWN), 10)
if thick_top_metal:
    stack.add_metal_layer(MetalLayer('ME6', 20*kA, 10 * mOhm_sq, DOWN), 12)
else:
    stack.add_metal_layer(MetalLayer('ME6', 7.0*kA, 30 * mOhm_sq, DOWN), 12)

# Add vias
# Via arguments: name, resistance, width or height (vias are assumed square),
#   spacing (defaults to 0)
# LayerStack.add_via arguments: via, bottom metal name, top metal name
stack.add_via(Via('CONT', 10 * Ohm, 0.15 * um, 0.20 * um), 'PO1', 'ME1')
stack.add_via(Via('VI1', 2 * Ohm, 0.20 * um, 0.20 * um), 'ME1', 'ME2')
stack.add_via(Via('VI2', 2 * Ohm, 0.20 * um, 0.20 * um), 'ME2', 'ME3')
stack.add_via(Via('VI3', 2 * Ohm, 0.20 * um, 0.20 * um), 'ME3', 'ME4')
stack.add_via(Via('VI4', 2 * Ohm, 0.20 * um, 0.20 * um), 'ME4', 'ME5')
stack.add_via(Via('VI5', 0.5 * Ohm, 0.50 * um, 0.60 * um), 'ME5', 'ME6')
# NOTE: when specifying spacing, the via layer's resistivity is calculated 
#   based on the effective via area. This allows to draw a single rectangle
#   instead of a large number of separate vias, which can significantly
#   decrease simulation times while still providing accurate results.
#   In order to obtain the most accurate model, the size of the single via 
#   rectangle should extend the area of the via array by exactly one half
#   of the spacing in both the x and y directions.


if __name__ == '__main__':
    # Print the full layer stack to example.pdf.
    # Be sure to carefully compare the generated stack to the stack
    # specification provided in the design kit.
    stack.draw('example', pages=3, single_page=True)
