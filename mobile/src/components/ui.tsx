import { ActivityIndicator, Pressable, StyleSheet, Text, TextInput, View, type TextInputProps, type ViewStyle } from "react-native";

export const colors = {
  ink: "#0b141a",
  ink2: "#18272f",
  text: "#13212a",
  muted: "#5d6d77",
  line: "#e2e7ea",
  bg: "#f3f5f6",
  panel: "#ffffff",
  brand: "#0f766a",
  brandDark: "#0d5f56",
  sos: "#b91c1c",
  sosDark: "#7f1d1d",
  warn: "#b45309",
  safe: "#15803d",
};

export function Screen({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[{ flex: 1, backgroundColor: colors.bg }, style]}>{children}</View>;
}

export function Card({ children, style }: { children: React.ReactNode; style?: ViewStyle }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function H1({ children }: { children: React.ReactNode }) {
  return <Text style={styles.h1}>{children}</Text>;
}

export function Label({ children }: { children: React.ReactNode }) {
  return <Text style={styles.label}>{children}</Text>;
}

export function Muted({ children, style }: { children: React.ReactNode; style?: object }) {
  return <Text style={[styles.muted, style]}>{children}</Text>;
}

export function Button({
  title,
  onPress,
  variant = "primary",
  loading,
  disabled,
  style,
}: {
  title: string;
  onPress: () => void;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
}) {
  const bg = { primary: colors.brand, secondary: colors.panel, danger: colors.sos, ghost: "transparent" }[variant];
  const fg = variant === "secondary" || variant === "ghost" ? colors.text : "#fff";
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: !!(disabled || loading) }}
      onPress={onPress}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: bg, opacity: disabled ? 0.5 : pressed ? 0.85 : 1 },
        variant === "secondary" && { borderWidth: 1, borderColor: colors.line },
        style,
      ]}
    >
      {loading ? <ActivityIndicator color={fg} /> : <Text style={[styles.buttonText, { color: fg }]}>{title}</Text>}
    </Pressable>
  );
}

export function Input(props: TextInputProps) {
  return <TextInput placeholderTextColor="#94a3b8" {...props} style={[styles.input, props.style]} />;
}

export function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      {typeof value === "string" || typeof value === "number" ? <Text style={styles.rowValue}>{value}</Text> : value}
    </View>
  );
}

export function Pill({ text, color = colors.muted, background = "#eef2f4" }: { text: string; color?: string; background?: string }) {
  return (
    <View style={{ alignSelf: "flex-start", borderRadius: 4, paddingHorizontal: 8, paddingVertical: 3, backgroundColor: background }}>
      <Text style={{ color, fontSize: 12, fontWeight: "600" }}>{text}</Text>
    </View>
  );
}

export function ErrorText({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <View style={styles.error} accessibilityRole="alert">
      <Text style={{ color: "#7f1d1d", fontSize: 14 }}>{message}</Text>
    </View>
  );
}

export function timeAgo(iso: string | number | null | undefined): string {
  if (iso == null) return "never";
  const t = typeof iso === "number" ? iso : new Date(/Z$|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`).getTime();
  const s = Math.max(0, Math.round((Date.now() - t) / 1000));
  if (s < 45) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return `${Math.round(s / 86400)} d ago`;
}

export const styles = StyleSheet.create({
  card: { backgroundColor: colors.panel, borderRadius: 10, borderWidth: 1, borderColor: colors.line, padding: 16 },
  h1: { fontSize: 24, fontWeight: "700", color: colors.text, letterSpacing: -0.3 },
  label: { fontSize: 11, fontWeight: "700", color: colors.muted, letterSpacing: 1, textTransform: "uppercase", marginBottom: 6 },
  muted: { color: colors.muted, fontSize: 14, lineHeight: 20 },
  button: { minHeight: 50, borderRadius: 8, alignItems: "center", justifyContent: "center", paddingHorizontal: 18 },
  buttonText: { fontSize: 16, fontWeight: "600" },
  input: { borderWidth: 1, borderColor: colors.line, backgroundColor: colors.panel, borderRadius: 8, paddingHorizontal: 14, minHeight: 50, fontSize: 16, color: colors.text },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingVertical: 8, gap: 12 },
  rowLabel: { color: colors.muted, fontSize: 14 },
  rowValue: { color: colors.text, fontSize: 14, fontWeight: "500", flexShrink: 1, textAlign: "right" },
  error: { backgroundColor: "#fee2e2", borderRadius: 8, padding: 12, marginTop: 8 },
});
