# INTERVIEW.md — DocAgent question bank

Answer format for every question: **Point → Reason → Proof → Trade-off** (≈ 25–40 seconds spoken).

---

## 1. Why did you build a baseline before the agent?
> I built the baseline first so I could compare before and after. Without it, saying the agent is better would just be a claim. The baseline gets 82% of fields right but only 50% of receipts fully correct, so every agent change has a clear number to beat. It also protects me from over-engineering: if the agent only added 2% at triple the cost, I'd keep the simple version.

## 2. Your field accuracy is 82%. Why do you report 50% as the main number?
> 50% is the number that matters to the business. If even one field on a receipt is wrong, a person has to review it. We get 82% of fields right, but only half the receipts are fully correct, so half still need a human. Field accuracy is still useful because it tells me which field to fix first — company was weakest at 75%.

## 3. Why is address fuzzy accuracy (92%) higher than exact (86%)?
> Six of the fourteen address "errors" are near-misses, not real mistakes. Fuzzy counts answers at least 90% similar to the correct one — like a missing ", JOHOR." at the end. So the real address problem is eight receipts, not fourteen, and that's where fixes should go first.

## 4. The agent reaches 90% fully correct at 3× the cost. Worth it?
> Compare against the cost of a human fixing documents. 3× of $0.0001 is $0.0003 per receipt; a person spending two minutes on one receipt costs about a thousand times more. Going from 50% to 90% removes 40 manual fixes per 100 receipts, so yes — unless latency matters more, like real-time checkout. Then I'd route only low-confidence receipts through the agent.
