import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { FlatList, Pressable, RefreshControl, Text, View } from "react-native";
import { Muted, Pill, Screen, colors, timeAgo } from "@/components/ui";
import { api } from "@/lib/api";

interface Note {
  id: number;
  category: string;
  title: string;
  body: string | null;
  created_at: string;
  read_at: string | null;
  related_sos_id: number | null;
}

export default function Alerts() {
  const [items, setItems] = useState<Note[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setItems(await api<Note[]>("/api/v1/me/notifications"));
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load alerts");
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(useCallback(() => void load(), [load]));

  async function open(n: Note) {
    if (!n.read_at) {
      api(`/api/v1/me/notifications/${n.id}/read`, { method: "POST" }).catch(() => undefined);
      setItems((prev) => prev.map((x) => (x.id === n.id ? { ...x, read_at: new Date().toISOString() } : x)));
    }
    if (n.related_sos_id) router.push(`/sos-status/${n.related_sos_id}`);
  }

  return (
    <Screen>
      <FlatList
        data={items}
        keyExtractor={(n) => String(n.id)}
        refreshControl={<RefreshControl refreshing={loading} onRefresh={load} />}
        contentContainerStyle={{ padding: 16, gap: 10 }}
        ListHeaderComponent={error ? <Text style={{ color: colors.sos }}>{error}</Text> : null}
        ListEmptyComponent={!loading ? <Muted style={{ textAlign: "center", marginTop: 40 }}>No alerts yet. Safety warnings and SOS updates will appear here.</Muted> : null}
        renderItem={({ item }) => (
          <Pressable onPress={() => open(item)} style={{ backgroundColor: item.read_at ? colors.panel : "#ecfdf5", borderRadius: 10, borderWidth: 1, borderColor: colors.line, padding: 14 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
              <Text style={{ fontWeight: "700", color: colors.text, flex: 1 }}>{item.title}</Text>
              <Text style={{ color: colors.muted, fontSize: 12 }}>{timeAgo(item.created_at)}</Text>
            </View>
            {item.body && <Muted style={{ marginTop: 4 }}>{item.body}</Muted>}
            <View style={{ marginTop: 8 }}>
              <Pill text={item.category.replace(/_/g, " ").toLowerCase()} />
            </View>
          </Pressable>
        )}
      />
    </Screen>
  );
}
