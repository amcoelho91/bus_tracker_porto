import "leaflet/dist/leaflet.css";
import { type TripExecution } from "../api/client";

interface TripSpineProps {
  execution: TripExecution[]; 
  routeColors: { bgColor: string; textColor: string };
}

export function TripSpine({ execution, routeColors }: TripSpineProps) {
  
    // Helper to get total minutes from either "HH:mm:ss" or ISO string
    const getMinutes = (timeStr: string) => {
        if (timeStr.includes('T')) {
        // It's an ISO string (UTC). Convert to local Date.
        const d = new Date(timeStr);
        return d.getHours() * 60 + d.getMinutes();
        }
        // It's a "HH:mm:ss" string
        const [h, m] = timeStr.split(':').map(Number);
        return h * 60 + m;
    };

    // Helper to format any time string to "HH:mm"
    const formatDisplayTime = (timeStr: string | null) => {
        if (!timeStr) return "--:--";
        if (timeStr.includes('T')) {
        const d = new Date(timeStr);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
        }
        return timeStr.substring(0, 5);
    };

    const getDeltaInfo = (planned: string, real: string | null) => {
        if (!real || !planned) return { text: null, value: null };
        
        const diff = getMinutes(real) - getMinutes(planned);
        const text = diff > 0 ? `+${diff}` : diff < 0 ? `–${diff*-1}` : "=";
        return { text, value: diff };
    };

  return (
    <div style={{ 
      padding: "10px", 
      background: "var(--bg-nav)", 
      overflowY: "auto", 
      color: "var(--text-main)",
      marginBottom: "20px"
    }}>
      <table style={{ width: "100%", borderCollapse: "collapse", border: "none", fontSize: "14px", tableLayout: "fixed" }}>
        <tbody>
          {execution.map((stop, idx) => {
            const isFirst = idx === 0;
            const isLast = idx === execution.length - 1;
            const { text: deltaText, value: deltaValue } = getDeltaInfo(
              stop.planned_arrival_time, 
              stop.real_arrival_time ?? stop.estimated_arrival_time
            );

            const isDelayAcceptable = deltaValue !== null && deltaValue >= -4 && deltaValue <= 5;
            const delayColor = isDelayAcceptable ? "#00b359" : "#ff4d4d";

            return (
              <tr key={idx} style={{ height: "40px", border: "none" }}>
                {/* SPINE */}
                <td style={{ width: "40px",  padding: 0, border: "none", position: "relative" }}>
                   <div style={{ display: "flex", flexDirection: "column", alignItems: "center", height: "40px" }}>
                    <div style={{ flex: 1, width: "8px", background: isFirst ? "transparent" : routeColors.bgColor }} />
                    {isFirst || isLast ? (
                      <div style={{ width: "20px", height: "20px", borderRadius: "50%", backgroundColor: routeColors.textColor, border: `6px solid ${routeColors.bgColor}`, zIndex: 2 }} />
                    ) : (
                      <div style={{ width: "8px", height: "100%", backgroundColor: routeColors.bgColor }} />
                    )}
                    <div style={{ flex: 1, width: "8px", background: isLast ? "transparent" : routeColors.bgColor }} />
                  </div>
                </td>

                {/* STOP NAME */}
                <td style={{ width: "auto", padding: "0 5px", whiteSpace: "nowrap", overflow: "hidden", 
                    textOverflow: "ellipsis", fontWeight: (isFirst || isLast) ? "bold" : "normal", 
                    border: "none" }}>
                  {(isFirst || isLast) ? (
                    stop.planned_stop_name.toLocaleUpperCase()
                    ) : (
                    stop.planned_stop_name
                  )}
                </td>

                {/* PLANNED STOP TIME */}
                <td style={{ width: "50px", alignItems: "center", textAlign: "center", opacity: 0.6, border: "none" }}>
                  {formatDisplayTime(stop.planned_arrival_time)}
                </td>

                {/* REAL OR ESTIMATED STOP TIME */}
                <td style={{ width: "50px", alignItems: "center", textAlign: "center", border: "none" }}>
                  {stop.real_arrival_time ? (
                    <div style={{ fontWeight: "600" }}>
                      {formatDisplayTime(stop.real_arrival_time)}
                    </div>
                  ) : stop.estimated_arrival_time ? (
                    <div style={{ fontSize: "11px", fontWeight: "300", 
                    color: "var(--text-secondary)", opacity: "0.6"}} >
                        {formatDisplayTime(stop.estimated_arrival_time)}
                    </div>
                  ) : (
                    <span style={{ opacity: 0.2, fontWeight: "300" }}>--:--</span>
                  )}
                </td>

                {/* REAL OR ESTIMATED DELAY */}
                <td style={{ width: "30px", textAlign: "center", paddingLeft: "0px", border: "none" }}>
                  {stop.real_arrival_time ? (
                    <div style={{ alignItems: "center",
                     fontWeight: "600", marginLeft: "0px", color: delayColor }}>
                      {deltaText}
                    </div>
                  ) : stop.estimated_arrival_time ? (
                    <div style={{ alignItems: "center",
                     fontSize: "11px", fontWeight: "150", marginLeft: "0px", color: delayColor }}>
                      {deltaText}
                    </div>
                  ) : (
                    <span style={{ alignItems: "center", opacity: 0.2, fontWeight: "300" }}>--</span>
                  )}
                </td>

                {/* DUMMY COLUMN: Takes all remaining space */}
                {/* <td style={{ width: "auto", border: "none" }}>&nbsp;</td> */}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}