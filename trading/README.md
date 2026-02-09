# Manni's Crypto Trading System

This repository contains the automated trading research and alert system.

## Structure
- `/trading/alert_scanner.py`: Hourly signal detection script.
- `/trading/sync_hyperliquid.py`: Data synchronization with Hyperliquid API.
- `/trading/strategies/`: Individual trading strategy implementations.
- `/trading/dashboard/`: Web-based monitoring terminal.
- `/trading/data/`: Database storage (SQLite).

## Setup
The system runs via cron jobs managed by OpenClaw. 
Dashboard is accessible at http://localhost:8080.
