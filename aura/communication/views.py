from django.shortcuts import render


def video_call(request, room_name):
    return render(
        request,
        "communication/video_call.html",
        {"room_name": room_name},
    )
