import { FlatList, Linking, RefreshControl, Text, View } from "react-native";
import { Button, Card, Label, Muted, Screen, colors } from "@/components/ui";
import { useLocation } from "@/lib/location";
import { FACILITY_COLOR, FACILITY_LABEL, type Facility, useNearbyHelp } from "@/lib/nearby";
import { formatDistance, navigationUrl } from "@/lib/url";

function FacilityRow({ f }: { f: Facility }) {
  return (
    <View style={{ backgroundColor: colors.panel, borderRadius: 10, borderWidth: 1, borderColor: colors.line, padding: 14, gap: 6 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: FACILITY_COLOR[f.facility_type] }} />
        <Text style={{ fontWeight: "700", color: colors.text, flex: 1 }}>{f.name}</Text>
        <Text style={{ color: colors.muted, fontSize: 12 }}>{formatDistance(f.distance_meters)}</Text>
      </View>
      <Muted>{FACILITY_LABEL[f.facility_type]}{f.address ? ` · ${f.address}` : ""}</Muted>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Button title="Navigate" onPress={() => Linking.openURL(navigationUrl(f.latitude, f.longitude))} style={{ flex: 1, minHeight: 42 }} />
        {f.phone && <Button title="Call" variant="secondary" onPress={() => Linking.openURL(`tel:${f.phone}`)} style={{ flex: 1, minHeight: 42 }} />}
      </View>
    </View>
  );
}

export default function NearbyHelp() {
  const { lastFix } = useLocation();
  const { data, error, loading, reload } = useNearbyHelp(
    lastFix ? Number(lastFix.latitude.toFixed(3)) : null,
    lastFix ? Number(lastFix.longitude.toFixed(3)) : null,
  );
  const key = [data?.police, data?.hospital, data?.fire_station].filter(Boolean) as Facility[];
  return (
    <Screen>
      <FlatList
        data={data?.nearby ?? []}
        keyExtractor={(f) => String(f.id)}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={reload} />}
        contentContainerStyle={{ padding: 16, gap: 10 }}
        ListHeaderComponent={
          <View style={{ gap: 10 }}>
            {error && <Text style={{ color: colors.sos }}>{error}</Text>}
            <Card style={{ gap: 6 }}>
              <Label>Emergency numbers</Label>
              <View style={{ flexDirection: "row", gap: 8 }}>
                <Button title="112" variant="danger" onPress={() => Linking.openURL("tel:112")} style={{ flex: 1, minHeight: 42 }} />
                <Button title="100 Police" variant="secondary" onPress={() => Linking.openURL("tel:100")} style={{ flex: 1, minHeight: 42 }} />
                <Button title="108 Ambulance" variant="secondary" onPress={() => Linking.openURL("tel:108")} style={{ flex: 1, minHeight: 42 }} />
              </View>
            </Card>
            {key.length > 0 && <Label>Closest by type</Label>}
            {key.map((f) => <FacilityRow key={`k${f.id}`} f={f} />)}
            {!!data?.nearby.length && <Label>Everything within 15 km</Label>}
          </View>
        }
        ListEmptyComponent={
          !loading && !error ? <Muted>No facilities on record near you. Ask the administrator to import the OpenStreetMap facility dataset.</Muted> : null
        }
        ListFooterComponent={<Muted style={{ fontSize: 11, marginTop: 8 }}>Facility data © OpenStreetMap contributors. Distances are straight-line.</Muted>}
        renderItem={({ item }) => <FacilityRow f={item} />}
      />
    </Screen>
  );
}
