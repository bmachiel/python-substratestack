#!/bin/env python

# import the technology's complete stack definition
from example import stack


# in order to decrease simulation times, some metal layers can be removed from
# the stack, allowing more oxide layers to be merged in the next step
stack.remove_metal_layer_by_name('PO1')
stack.remove_metal_layer_by_name('ME1')
stack.remove_metal_layer_by_name('ME2')
stack.remove_metal_layer_by_name('ME3')
stack.remove_metal_layer_by_name('ME4')
#stack.remove_metal_layer_by_name('ME5')
#stack.remove_metal_layer_by_name('ME6')

if __name__ == '__main__':
    # Print the standardized stack to example_ME5ME6_std.pdf
    stack.draw('example_ME5ME6_std', pages=3, single_page=True)

# Merge oxide layers to reduce the stack's complexity, decreasing simulation
# times
stack.simplify()

if __name__ == '__main__':
    # Print the simplified stack to example_ME5ME6.pdf
    stack.draw('example_ME5ME6', pages=3, single_page=True)

    # Write out a Momentum subtrate definition file of the simplified stack
    # write_momentum_substrate argument: filename (without extension), 
    #                                    infinite ground plane
    # NOTE: this might produce bad output when the stack has not been
    #   simplified before!
    stack.write_momentum_substrate('example_ME5ME6', True)

    # Write out a Sonnet project that includes the simplified subtrate stack
    # write_sonnet_technology argument: filename (without extension)
    # NOTE: this might produce bad output when the stack has not been
    #   simplified before!
    stack.write_sonnet_technology('example_ME5ME6')
