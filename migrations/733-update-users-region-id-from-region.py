from users.models import UserProfile

for user in UserProfile.objects.all():
    user.region_id = getattr(user.region, 'id', None)
    if user.region_id is not None:
        user.save()
