import { useEffect, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { Card, Label, Muted, Pill, Screen, colors } from "@/components/ui";
import { api } from "@/lib/api";

interface Advisory {
  code: string;
  risk_level: string;
  reason: string;
  recommended_action: string;
}

interface Report {
  risk_score: number;
  risk_level: string;
  advisories: Advisory[];
  confidence_note: string;
  features: { point_count: number; total_distance_m: number; stationary_minutes: number };
  recent_geofence_events: { event_type: string; zone_name: string | null; created_at: string }[];
}

const LEVEL_COLOR: Record<string, string> = { LOW: "#15803d", MEDIUM: "#b45309", HIGH: "#c2410c", CRITICAL: "#b91c1c" };

export default function SafetyReport() {
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api<Report>("/api/v1/me/safety-report").then(setReport).catch((e) => setError(e.message));
  }, []);

  if (error) return <Screen style={{ padding: 16 }}><Text style={{ color: colors.sos }}>{error}</Text></Screen>;
  if (!report) return <Screen style={{ padding: 16 }}><Muted>Loading your safety report…</Muted></Screen>;
  return (
    <Screen>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
        <Card>
          <Label>Last 24 hours</Label>
          <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 10 }}>
            <Text style={{ fontSize: 40, fontWeight: "800", color: LEVEL_COLOR[report.risk_level] ?? colors.text }}>{report.risk_score}</Text>
            <Text style={{ color: colors.muted, marginBottom: 8 }}>/ 100 risk score · {report.risk_level.toLowerCase()}</Text>
          </View>
          <Muted>
            {report.features.point_count} location points · {(report.features.total_distance_m / 1000).toFixed(1)} km travelled
          </Muted>
          <Muted style={{ marginTop: 6, fontSize: 12 }}>{report.confidence_note}</Muted>
        </Card>
        <Card style={{ gap: 12 }}>
          <Label>Advisories</Label>
          {!report.advisories.length && <Muted>No advisories. This means no rule fired, not that every risk is known.</Muted>}
          {report.advisories.map((a, i) => (
            <View key={i} style={{ gap: 4 }}>
              <Pill text={a.risk_level.toLowerCase()} color="#fff" background={LEVEL_COLOR[a.risk_level] ?? colors.muted} />
              <Text style={{ color: colors.text, fontWeight: "600" }}>{a.reason}</Text>
              <Muted>{a.recommended_action}</Muted>
            </View>
          ))}
        </Card>
        <Card>
          <Label>Zone entries and exits</Label>
          {!report.recent_geofence_events.length && <Muted>None in the last 24 hours.</Muted>}
          {report.recent_geofence_events.map((e, i) => (
            <Muted key={i}>
              {e.event_type === "ENTER" ? "Entered" : "Left"} {e.zone_name ?? "a zone"} · {new Date(e.created_at).toLocaleTimeString()}
            </Muted>
          ))}
        </Card>
      </ScrollView>
    </Screen>
  );
}
