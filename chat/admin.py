from django.contrib import admin

from .models import Room, Message, ConvoSummary, ServiceRating

admin.site.register(Room)
admin.site.register(Message)
admin.site.register(ConvoSummary)
admin.site.register(ServiceRating)