

def get_config_for_policy(policy, faulty = False):
    enforcer_action = 'add_call'

    if 'bluetooth-adapter' == policy:
        target_apk           = 'resources/apk/bluechat.apk'
        target_apk_faulty    = 'resources/apk/bluechat-faulty.apk'
        automaton            = 'resources/automaton/bluetooth-adapter.json'
        default_enforcer_apk = 'bluetooth-adapter-enforcer.apk'
        enforcer_package     = 'com.proactive.bluetoothadapterenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.bluetoothadapterenforcer-1/base.apk'

    elif 'camera' == policy:
        target_apk           = 'resources/apk/foocam.apk'
        target_apk_faulty    = 'resources/apk/foocam-release-faulty.apk'
        automaton            = 'resources/automaton/camera.json'
        default_enforcer_apk = 'camera-enforcer.apk'
        enforcer_package     = 'com.proactive.cameraenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.cameraenforcer-1/base.apk'

    elif 'camera-preview' == policy:
        target_apk           = 'resources/apk/foocam.apk'
        target_apk_faulty    = 'resources/apk/foocam-camerapreview-faulty.apk'
        automaton            = 'resources/automaton/camera-preview.json'
        default_enforcer_apk = 'camera-preview-enforcer.apk'
        enforcer_package     = 'com.proactive.camerapreviewenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.camerapreviewenforcer-1/base.apk'

    elif 'location-manager' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-location-manager-faulty.apk'
        automaton            = 'resources/automaton/location-manager.json'
        default_enforcer_apk = 'location-manager-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.locationmanagerenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.locationmanagerenforcer-1/base.apk'

    elif 'location-manager-service' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-location-manager-faulty.apk'
        automaton            = 'resources/automaton/location-manager-service.json'
        default_enforcer_apk = 'location-manager-service-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.locationmanagerserviceenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.locationmanagerserviceenforcer-1/base.apk'

    elif 'lru-cache' == policy:
        target_apk           = 'resources/apk/popmovies.apk'
        target_apk_faulty    = 'resources/apk/popmovies-faulty.apk'
        automaton            = 'resources/automaton/lru-cache.json'
        default_enforcer_apk = 'lrucacheconstructor-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.lrucacheconstructorenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.lrucacheconstructorenforcer-1/base.apk'

    elif 'media-player-constructor' == policy:
        target_apk           = 'resources/apk/sample-music-player-constructor.apk'
        target_apk_faulty    = 'resources/apk/sample-music-player-constructor-faulty.apk'
        automaton            = 'resources/automaton/media-player-constructor.json'
        default_enforcer_apk = 'media-player-constructor-enforcer.apk'
        enforcer_package     = 'com.proactive.mediaplayerconstructorenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.mediaplayerconstructorenforcer-1/base.apk'

    elif 'media-player-create' == policy:
        target_apk           = 'resources/apk/sample-music-player-create.apk'
        target_apk_faulty    = 'resources/apk/sample-music-player-create-faulty.apk'
        automaton            = 'resources/automaton/media-player-create.json'
        default_enforcer_apk = 'media-player-create-enforcer.apk'
        enforcer_package     = 'com.proactive.mediaplayercreateenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.mediaplayercreateenforcer-1/base.apk'

    elif 'remote-callback-list' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-remote-callback-list-faulty.apk'
        automaton            = 'resources/automaton/remote-callback-list.json'
        default_enforcer_apk = 'remote-callback-list-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.remotecallbacklistenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.remotecallbacklistenforcer-1/base.apk'

    elif 'remote-callback-list-service' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-remote-callback-list-faulty.apk'
        automaton            = 'resources/automaton/remote-callback-list-service.json'
        default_enforcer_apk = 'remote-callback-list-service-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.remotecallbacklistserviceenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.remotecallbacklistserviceenforcer-1/base.apk'

    elif 'sensor-manager' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-sensor-manager-faulty.apk'
        automaton            = 'resources/automaton/sensor-manager.json'
        default_enforcer_apk = 'sensor-manager-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.sensormanagerenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.sensormanagerenforcer-1/base.apk'

    elif 'sensor-manager-service' == policy:
        target_apk           = 'resources/apk/getbackgps.apk'
        target_apk_faulty    = 'resources/apk/getbackgps-sensor-manager-faulty.apk'
        automaton            = 'resources/automaton/sensor-manager-service.json'
        default_enforcer_apk = 'sensor-manager-service-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.sensormanagerserviceenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.sensormanagerserviceenforcer-1/base.apk'

    elif 'thread' == policy:
        target_apk           = 'resources/apk/wifi-saver.apk'
        target_apk_faulty    = 'resources/apk/wifi-saver-faulty.apk'
        automaton            = 'resources/automaton/thread.json'
        default_enforcer_apk = 'thread-enforcer.apk'
        enforcer_package     = 'com.proactive.threadenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.threadenforcer-1/base.apk'

    elif 'wakelock' == policy:
        target_apk           = 'resources/apk/wakelock.apk'
        target_apk_faulty    = 'resources/apk/wakelock-faulty.apk'
        automaton            = 'resources/automaton/wakelock.json'
        default_enforcer_apk = 'wakelock-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.wakelockenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.wakelockenforcer-1/base.apk'

    elif 'wifi-multicast-lock' == policy:
        target_apk           = 'resources/apk/multicast-tester.apk'
        target_apk_faulty    = 'resources/apk/multicast-tester-release-faulty.apk'
        automaton            = 'resources/automaton/wifi-multicast-lock.json'
        default_enforcer_apk = 'wifi-multicast-lock-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.wifimulticastlockenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.wifimulticastlockenforcer-1/base.apk'

    # -----------------------------

    elif 'media-recorder-camera' == policy:
        enforcer_action      = 'prevent_call'
        target_apk           = 'resources/apk/video-recorder-camera.apk'
        target_apk_faulty    = 'resources/apk/video-recorder-camera-faulty.apk'
        automaton            = 'resources/automaton/media-recorder-camera.json'
        default_enforcer_apk = 'media-recorder-camera-enforcer.apk'
        enforcer_package     = 'com.proactive.mediarecordercameraenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.mediarecordercameraenforcer-1/base.apk'

    # ------------------------------

    elif 'managed-query' == policy:
        enforcer_action      = 'replace_call'
        target_apk           = 'resources/apk/contact-list.apk'
        target_apk_faulty    = 'resources/apk/contact-list-faulty.apk'
        automaton            = 'resources/automaton/managed-query.json'
        default_enforcer_apk = 'managed-query-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.managedqueryenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.managedqueryenforcer-1/base.apk'

    elif 'get-drawable' == policy:
        enforcer_action      = 'replace_call'
        target_apk           = 'resources/apk/popmovies.apk'
        target_apk_faulty    = 'resources/apk/popmovies-drawable-faulty.apk'
        automaton            = 'resources/automaton/get-drawable.json'
        default_enforcer_apk = 'get-drawable-enforcer-forced.apk'
        enforcer_package     = 'com.proactive.getdrawableenforcer'
        enforcer_apk_path    = '/data/app/com.proactive.getdrawableenforcer-1/base.apk'

    else:
        raise Exception(f'Unsupported policy {policy}!')

    target_apk = target_apk if not faulty else target_apk_faulty
    return {
        'target_apk': target_apk,
        'automaton': automaton,
        'default_enforcer_apk': default_enforcer_apk,
        'enforcer_package': enforcer_package,
        'enforcer_apk_path': enforcer_apk_path,
        'enforcer_action': enforcer_action,
    }
