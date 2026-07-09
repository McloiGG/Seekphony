/// <reference types="vite/client" />

interface SeekphonyRuntimeConfig {
  apiBaseUrl?: string;
}

interface Window {
  __SEEKPHONY_CONFIG__?: SeekphonyRuntimeConfig;
  webkitAudioContext?: typeof AudioContext;
}
