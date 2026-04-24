Epic Systems & Azure OpenAI – AI Capacity & Quota Management    

Purpose 

This document explains how Azure OpenAI capacity and Quota are requested, approved, and provisioned. It is intended to help internal teams (TPMs, CSAMs, PMs) and strategic ISV customers (e.g., Epic Systems) understand: 

Group 203, Grouped object 

 

 

 

 

 

 

Which path to use (PAYGO or  PTU) 

Expected timelines 

When escalation is required (UAT)   

Key Definitions 

Quota  

The customer’s allowed limit to request or consume Azure OpenAI resources 
(e.g., TPMs, PTUs). 

Capacity 

The underlying GPU availability required to serve the requested quota. 

Important: Having quota does not guarantee immediate capacity, especially for: 

Constrained models 

Large requests 

Region‑specific / sovereignty‑restricted deployments 

Capacity Request Paths – Overview 

Azure OpenAI capacity is managed through 2 primary paths: 

PAYGO (Pay‑As‑You‑Go) 

PTU (Provisioned Throughput Units) 

The correct path depends on: 

Model type 

Size of request 

Capacity availability 

Regional constraints 

1. PAYGO (Pay‑As‑You‑Go) 

When to Use 

Default path for most customers 

Suitable for non‑constrained models 

Requests typically auto‑approved up to 2× default quota 

Key Rules 

Requests above 2× default quota → UAT required 

Some newer or constrained models (e.g., GPT‑5.2) may not have immediate capacity 

Expected Timeline 

Non‑constrained models: ~ 3 business days 

Constrained models: Reviewed in weekly triage; ETA depends. See UAT process in following section. 

2. PTU (Provisioned Throughput Units) 

When to Use 

Customers requiring predictable, reserved throughput 

Designed to be self‑service where possible 

How PTU Works 

Customer requests PTU quota 

Capacity availability is checked via internal tools 

If quota and capacity exist → provisioning proceeds without UAT 

Guardrails 

Auto‑approval limits (typical):  

~ 1000 PTUs (regional) 

~ 3000 PTUs (global) 

When UAT Is Required 

Large requests (≈ 500–1000+ PTUs) 

Capacity not visible in tooling 

Requests needing advance planning 

Capacity Build Considerations 

GPU reallocation or build‑out can take up to ~2 weeks 
Early planning is critical for large PTU asks. 

Escalation & Special Asks - UAT (Unified Action Tracker) 

 All escalations for AI capacity must go through weekly UAT. Happens every Thur. 

When UAT Is Required 

Quota request exceeds auto‑approval limits 

Capacity not immediately available 

Large PTU requests needing planning 

Customer requires specific regions due to sovereignty or compliance 

What Happens in UAT 

Request reviewed by the AI Capacity team 

Capacity evaluated across global and regional pools 

Constrained models reviewed during weekly (Thursday) triage 

Prioritization & Triage Considerations 

UAT requests are prioritized based on: 

Strategic importance of the customer 

Azure commitment and consumption breadth 

Business impact and production timelines 

Quality of forecasting and advance notice 

Note: Last‑minute, large, poorly forecasted requests may face delays or partial enablement. 

Regional vs Global Capacity 

AI capacity is managed in global / data‑zone pools 

Customer‑imposed constraints (e.g., UK‑only, state‑level residency, HIPAA) reduce flexibility 

Accepting global or multi‑region capacity often improves approval speed 

Strict regional requirements depend on local GPU health 

Visual Decision Flow 

START 
  | 
  |-- Is the customer using PAYGO? 
  |       | 
  |       |-- Model non‑constrained AND request ≤ 2× default quota? 
  |       |        → Auto‑approved (PAYGO) 
  |       | 
  |       |-- Constrained model OR request > 2× default? 
  |                → Raise UAT 
  | 
  |-- Is the customer requesting PTU? 
          | 
          |-- PTU within limits AND capacity visible? 
          |        → Self‑serve PTU provisioning 
          | 
          |-- Large PTU ask (500–1000+) OR no capacity visible? 
                   → Raise UAT (planning required) 
  

Key Links & Contacts 

AI Capacity Hub: https://aka.ms/aicapacityhub 

Azure OpenAI Solution Sizing Tool: 
https://aoaisolutionsizingtool.azurewebsites.net 

AI Capacity Team Alias: aicapacity@microsoft.com 

Recommended Best Practices 

Forecast demand weeks in advance 

Validate quota hygiene before escalation 

Clear document:  

Business impact 

Production timelines 

Regional / sovereignty constraints 

Use UAT early for large or constrained requests 

 