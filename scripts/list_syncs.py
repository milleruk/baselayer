from peloton.models import PelotonConnection
from django.utils import timezone

now = timezone.now()
qs = PelotonConnection.objects.filter(sync_in_progress=True)
print('Found', qs.count(), 'connections with sync_in_progress=True')
for c in qs:
    age = (now - c.sync_started_at).total_seconds() / 60 if c.sync_started_at else None
    print("id=%s user_id=%s email=%s started_at=%s age_min=%s last_sync_at=%s cooldown_until=%s" % (
        c.id, getattr(c.user, 'id', None), getattr(c.user, 'email', None),
        c.sync_started_at, ('%.1f' % age) if age is not None else 'None', c.last_sync_at, c.sync_cooldown_until
    ))
