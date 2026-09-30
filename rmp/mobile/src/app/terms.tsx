import { Stack } from "expo-router";
import { Text } from "react-native";
import { Screen } from "@/components/Screen";
import { Card, ui } from "@/components/NativeUI";

export default function TermsScreen() {
  return (
    <Screen>
      <Stack.Screen options={{ title: "Terms of Use" }} />
      <Text style={ui.title}>Terms of Use</Text>
      <Text style={ui.copy}>Last updated September 30, 2026</Text>
      <Card>
        <Text style={ui.heading}>Entertainment pools</Text>
        <Text style={ui.copy}>Run My Pool is an entertainment service for sports pools. The app does not accept wagers, entry fees, or payments, and does not distribute prizes.</Text>
      </Card>
      <Card>
        <Text style={ui.heading}>Participant features</Text>
        <Text style={ui.copy}>The mobile app lets invited members manage their entries and picks and view pool standings and results. It does not include a forum, chat, direct messaging, or other member-posting feature.</Text>
      </Card>
      <Card>
        <Text style={ui.heading}>Your agreement</Text>
        <Text style={ui.copy}>By signing in, you agree to follow these Terms of Use. You may contact support@runmypool.net with an account, support, or privacy question.</Text>
      </Card>
    </Screen>
  );
}
