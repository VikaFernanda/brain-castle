// One place that binds htm to Preact's h, so every file writes: html`<div>...</div>`
import { h } from 'preact';
import htm from 'htm';
export const html = htm.bind(h);
