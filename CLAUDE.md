# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

HappyRobot FDE Technical Challenge — build a backend API + conversational AI agent that handles inbound calls from freight carriers wanting to book loads. The agent acts as an automated sales representative for a fictional company "Acme Logistics".

## Agent Conversation Flow

The agent must handle a 6-step interaction:

1. **Authenticate** carrier via MC number → verify with the FMCSA API
2. **Search loads** from the database and pitch the best match
3. **Ask** if the carrier wants to accept the load
4. **Negotiate** — handle up to 3 counter-offers with pricing logic
5. **Transfer** the call to a human sales rep if price is agreed
6. **Post-call extraction & classification** — pull key data, classify outcome + carrier sentiment

## Architecture

- **Agent**: Conversational flow engine managing the 6-step carrier interaction
- **Backend API**: REST API serving the agent, loads database, and metrics
- **FMCSA Integration**: Carrier authentication via MC number lookup
- **Metrics Dashboard**: Call outcomes, sentiment analysis, and operational metrics
- **Deployment**: Docker container on Railway
