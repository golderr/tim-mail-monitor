import { ImageResponse } from "next/og";

export const size = {
  width: 32,
  height: 32,
};

export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: "center",
          background: "linear-gradient(180deg, #f8fbff 0%, #dbe7f6 100%)",
          display: "flex",
          height: "100%",
          justifyContent: "center",
          width: "100%",
        }}
      >
        <div
          style={{
            background: "#ffffff",
            border: "2px solid #173d73",
            borderRadius: "6px",
            boxShadow: "0 2px 6px rgba(23, 61, 115, 0.14)",
            display: "flex",
            height: "22px",
            overflow: "hidden",
            position: "relative",
            width: "24px",
          }}
        >
          <div
            style={{
              borderLeft: "10px solid transparent",
              borderRight: "10px solid transparent",
              borderTop: "9px solid #173d73",
              height: 0,
              left: "1px",
              position: "absolute",
              top: "1px",
              width: 0,
            }}
          />
          <div
            style={{
              borderLeft: "11px solid transparent",
              borderRight: "11px solid transparent",
              borderTop: "10px solid #ffffff",
              height: 0,
              left: 0,
              position: "absolute",
              top: 0,
              width: 0,
            }}
          />
          <div
            style={{
              background: "#173d73",
              borderRadius: "999px",
              height: "4px",
              left: "15px",
              position: "absolute",
              top: "6px",
              width: "4px",
            }}
          />
        </div>
      </div>
    ),
    {
      ...size,
    },
  );
}
