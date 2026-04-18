from django.dispatch import Signal


# fired any time a device is created
# providing_args=["device"]
device_created = Signal()


# fired any time a device is updated
# providing_args=["device"]
device_updated = Signal()
