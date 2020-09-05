from peewee import *

db = SqliteDatabase('rou.db')


class PickupStatus:
    default = 0
    seat_full = 1


class PickupType:
    unknown = 0
    netflix = 1
    hbo = 2
    spotify = 3
    hulu = 4
    apple = 5
    duan = 6
    password = 7
    youtube = 8
    tidal = 9
    office = 10


class Pickup(Model):
    type = IntegerField(default=PickupType.unknown)
    message = CharField()
    poster = CharField()
    poster_name = CharField()
    post_date = DateTimeField()
    status = IntegerField(default=PickupStatus.default)

    class Meta:
        database = db
