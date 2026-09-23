def saved_vehicle_ids(user):
    if not user.is_authenticated:
        return set()
    return set(user.saved_vehicles.values_list('vehicle_id', flat=True))
