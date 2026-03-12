BASE="http://localhost:8001"

echo "BEFORE:"
echo "Patients:"
curl -s "$BASE/api/patients"
echo -e "\nAppointments:"
curl -s "$BASE/api/appointments"
echo -e "\n"

echo "Sending fake WhatsApp message..."
curl -s -X POST "$BASE/api/webhook/whatsapp" \
  -H "Content-Type: application/json" \
  -d '{
    "entry": [{
      "changes": [{
        "value": {
          "messages": [{
            "from": "+919876543210",
            "id": "test999",
            "text": { "body": "I need an appointment tomorrow at 4 pm for tooth pain" }
          }]
        }
      }]
    }]
  }'
echo -e "\n"

sleep 2

echo "AFTER:"
echo "Patients:"
curl -s "$BASE/api/patients"
echo -e "\nAppointments:"
curl -s "$BASE/api/appointments"
echo -e "\n"