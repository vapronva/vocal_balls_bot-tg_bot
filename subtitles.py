from models import SpeechRecognitionVoskPartialResult


def genereate_vtt_subs(results: list[SpeechRecognitionVoskPartialResult]) -> str:
    resultingVTT = "WEBVTT\n\n"
    for result in results:
        startTime = f"{int(result.startTime // 3600):02d}:{int(result.startTime // 60) - int(result.startTime // 3600) * 60:02d}:{result.startTime % 60:06.3f}"
        endTime = f"{int(result.endTime // 3600):02d}:{int(result.endTime // 60) - int(result.endTime // 3600) * 60:02d}:{result.endTime % 60:06.3f}"
        resultingVTT += f"{startTime} --> {endTime}\n{result.text}\n\n"
    return resultingVTT
