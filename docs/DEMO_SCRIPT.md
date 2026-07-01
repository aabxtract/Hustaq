# Hustaq Demo Script

### Preparation
1. Ensure Vercel deployment is healthy (`GET /api/health` returns 200).
2. Ensure MongoDB has the demo seller.
3. Keep this script and terminal open.

### The Loop
1. **Seller Onboarding**: As a seller, text the Hustaq bot number: "I want to sell". Complete the onboarding steps.
2. **Browse Catalog**: As a buyer, text the seller's Twilio number: "Hi".
3. **Checkout**: Reply "1" to view the product detail, "1" to buy, type the quantity, and confirm.
4. **Delivery**: Reply "CONFIRM" and type an address. You will receive an order summary with real Nomba bank details.
5. **Nomba Webhook**: Run the Nomba curl command in the terminal to fire a `payment.success` event. Replace `ORDER_ID_HERE` with the actual order ID in MongoDB.
   ```bash
   curl -X POST https://your-project.vercel.app/api/webhooks/nomba \
     -H 'Content-Type: application/json' \
     -d '{
       "event": "payment.success",
       "data": {
         "reference": "NOM-TEST-001",
         "orderId": "ORDER_ID_HERE",
         "amount": "25500",
         "status": "success",
         "customer": { "name": "Chijioke", "phone": "+2348051234567" }
       }
     }'
   ```
6. **Notifications**: Both buyer and seller phones will receive notifications.
