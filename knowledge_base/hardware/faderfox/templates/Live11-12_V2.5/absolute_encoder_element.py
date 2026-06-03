from ableton.v2.control_surface.elements import EncoderElement

class AbsoluteEncoderElement(EncoderElement):
    def normalize_value(self, value):
        return value

    def set_light(self, value):
        pass
