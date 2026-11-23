import { useEffect, useRef, useState } from "react";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

export default function WebcamCapture({ count = 8, intervalMs = 700, onDone, disabled }) {
  const videoRef = useRef(null);
  const [err, setErr] = useState("");
  const [progress, setProgress] = useState(0);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let stream;
    navigator.mediaDevices
      .getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false })
      .then((s) => { stream = s; if (videoRef.current) videoRef.current.srcObject = s; })
      .catch(() => setErr("Cannot access the webcam. Allow camera permission in the browser and retry."));
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  const start = async () => {
    const v = videoRef.current;
    if (!v || !v.videoWidth) return setErr("Camera is not ready yet.");
    setRunning(true);
    setProgress(0);
    const canvas = document.createElement("canvas");
    canvas.width = v.videoWidth;
    canvas.height = v.videoHeight;
    const shots = [];
    for (let i = 0; i < count; i++) {
      canvas.getContext("2d").drawImage(v, 0, 0);
      shots.push(canvas.toDataURL("image/jpeg", 0.92));
      setProgress(i + 1);
      await sleep(intervalMs);
    }
    setRunning(false);
    onDone(shots);
  };

  return (
    <div className="webcam">
      <video ref={videoRef} autoPlay muted playsInline />
      {err && <div className="notice error">{err}</div>}
      <p className="muted">Face the camera in good light. During capture, slowly turn your head a little left, right, up and down.</p>
      <button className="primary" onClick={start} disabled={running || disabled || !!err}>
        {running ? `Capturing ${progress}/${count}…` : "Capture face samples"}
      </button>
    </div>
  );
}
