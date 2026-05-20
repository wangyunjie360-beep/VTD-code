# Triggered Deceleration

## User Request
Create an OpenSCENARIO XML scenario where `ego` drives at a steady speed until a trigger fires, then decelerates smoothly to a slower target speed. Use a conservative trigger and keep the document minimal.

## Coverage Expectations
- One vehicle with clear init speed
- One trigger that starts the deceleration behavior
- A deceleration action that changes speed without adding unrelated maneuvers
- A bounded stop condition or explicit end state
