"""Render an explicit frame range through MLT to MP4, WebM, ProRes MOV or WAV. Poll core jobs_get_status; use jobs_cancel to cancel."""

from dcc_mcp_kdenlive.render import render_project


def main(**kwargs):
    return render_project(**kwargs)
