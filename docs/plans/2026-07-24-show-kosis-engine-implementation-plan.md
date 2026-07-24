# KOSIS Engine Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Display whether stored verification used real KOSIS API or a fixture.

**Architecture:** Render a caption from audit_json.engine and processed_at in render_stored_claim.

**Tech Stack:** Python, Streamlit, pytest.

### Task 1
Add a source regression test, verify RED, then render engine labels for HttpKosisClient, FixtureKosisClient, and missing audit data. Run targeted tests and commit.
