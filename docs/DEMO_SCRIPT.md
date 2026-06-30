# Hustaq Demo Script

Follow these steps precisely during your demo to show the full end-to-end flow. 
Make sure you have your phone ready and your terminal open.

## Step 1: Seller Onboarding & Adding a Product
**Action**: From the seller's phone, send a message to the Hustaq central bot number.
1. **Seller**: `I want to sell`
2. **Bot**: *Welcome to Hustaq! ... Ready to set up your shop? Reply YES to continue.*
3. **Seller**: `Yes`
4. **Bot**: *What is your shop name?*
5. **Seller**: `Amina Fabrics`
6. **Bot**: *What do you sell? ...*
7. **Seller**: `1` *(Fashion)*
8. **Bot**: *Where are you based?*
9. **Seller**: `Yaba Lagos`
10. **Bot**: *Your shop "Amina Fabrics" is live... Send a photo to add your first product.*
11. **Seller**: *(Sends a photo of Ankara fabric)*
12. **Bot**: *Got the photo! What is the product name?*
13. **Seller**: `Hollandaise Ankara`
14. **Bot**: *What is the price in Naira?*
15. **Seller**: `8500`

## Step 2: Buyer Browsing & Ordering
**Action**: From a second phone (the buyer), send a message to the seller's designated Twilio number.
1. **Buyer**: `Hi`
2. **Bot**: *Hi! Welcome to Amina Fabrics. Here is what we have: 1. Hollandaise Ankara...*
3. **Buyer**: `1`
4. **Bot**: *Hollandaise Ankara - N8,500 ... 1. Buy now...*
5. **Buyer**: `1`
6. **Bot**: *How many would you like?*
7. **Buyer**: `3`
8. **Bot**: *3 x N8,500 = N25,500. Reply CONFIRM...*
9. **Buyer**: `CONFIRM`
10. **Bot**: *Great! Where should we deliver? Type your full address.*
11. **Buyer**: `12 Herbert Macaulay Way, Yaba`
12. **Bot**: *Order Summary ... Pay to: Amina Fabrics ... Reply PAID when you have transferred.*

## Step 3: Payment Webhook Simulation (The "Aha!" Moment)
**Action**: In your terminal, run the following `curl` command to simulate Nomba sending a successful payment webhook.
*(Ensure you replace `<YOUR_LAMBDA_URL>` and `<ORDER_ID_FROM_DATABASE>` beforehand, or just point out how this works!)*

```bash
curl -X POST <YOUR_LAMBDA_URL>/webhooks/nomba \
  -H 'Content-Type: application/json' \
  -d '{
    "event": "payment.success",
    "data": {
      "reference": "NOM-TEST-001",
      "orderId": "<ORDER_ID_FROM_DATABASE>",
      "amount": "25500",
      "status": "success",
      "customer": { "name": "Buyer", "phone": "+2348000000000" }
    }
  }'
```

## Step 4: The Dual Notification
**Action**: Watch both phones.
1. **Buyer's Phone**: *Payment received! Order #... confirmed.*
2. **Seller's Phone**: *New order #... - N25,500 - PAID*

**Demo Complete!**
