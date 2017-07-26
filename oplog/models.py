from django.db import models
from django.utils import timezone;

# Create your models here.


class OpLog(models.Model):
    """ Save the app op logs in the db.
    Args:
        user: an sso user_name
        op: should be one of the following operations
            reposit
            delete
            deploy
            update
            update
            lock
            scale
        app: the app name
        app_version: if the op is deploy, the app_version is the new version.
        time: the time when the op is begin 
        message: if the op is lock, is the user's input message; otherwise will be description for the op
    """
    user = models.CharField(max_length=64)
    op = models.CharField(max_length=16)
    app = models.CharField(max_length=32)
    app_version = models.CharField(max_length=128)
    time = models.DateTimeField()
    message = models.CharField(max_length=512)

def _add_oplog(user, op, app, app_version, message):
    try:
        time = timezone.localtime(timezone.now())
        oplog = OpLog(user=user, op=op, app=app,
                      app_version=app_version, time=time, message=message)
        oplog.save()
    except:
        pass

def add_oplog(user, op, app, app_version, message):
    from threading import Thread
    t = Thread(target=_add_oplog, args=(user, op, app, app_version, message))
    t.start()

