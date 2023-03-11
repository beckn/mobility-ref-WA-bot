# mobility-ref-WA-bot

It is a Whatsapp based bot for mobility. 

**Capabilities**:
1. Get user start location.
2. Get user destination locattion
3. Find/Book/Track rides.

**Usage:**
1. Install the requirements as 
    ```python
    pip  install -r requirements.txt
    ```
2. Update config.yaml with necessary credentials.
3. Update customer/beckn/beckn.json with gupshup credentials,
4. Provide a database name in customer/beckn/beckn.json. DB gets created internally
   during the flow.
5. Start the server as :
```python
uvicorn runner.launcher:app --port <port_number> --host 0.0.0.0
```

***Note**: Please ensure port is open and not in use already*

**Requirements:**
1. Python 3.9
2. MongoDB
3. GupShup account
4. Google Maps 
