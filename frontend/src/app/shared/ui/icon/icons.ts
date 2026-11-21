/**
 * Central Icon Code Store / Registry
 * -------------------------------------------------------------
 * Store all your SVG icons here in one centralized location!
 *
 * To add a new icon:
 * 1. Choose a unique name key (e.g. 'my-new-icon').
 * 2. Paste your raw <svg>...</svg> code as the value.
 *
 * Tips:
 * - Use `stroke="currentColor"` or `fill="currentColor"` so the
 *   icon inherits dynamic colors from <app-icon [color]="...">.
 * - The <app-icon> component automatically normalizes width/height
 *   to scale seamlessly to any size specified via <app-icon [size]="...">.
 */

export const APP_ICONS: Record<string, string> = {
  // Collapse icon (Double left chevrons - requested by user)
  collapse: `<svg width="13" height="12" viewBox="0 0 13 12" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M6.17871 10.833L1.17871 5.83301L6.17871 0.833008M11.1787 10.833L6.17871 5.83301L11.1787 0.833008" stroke="currentColor" stroke-width="1.66667" stroke-linecap="round"/>
</svg>`,

  // Expand icon (Double right chevrons)
  expand: `<svg width="13" height="12" viewBox="0 0 13 12" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M6.82129 0.833008L11.8213 5.83301L6.82129 10.833M1.82129 0.833008L6.82129 5.83301L1.82129 10.833" stroke="currentColor" stroke-width="1.66667" stroke-linecap="round"/>
</svg>`,

  // Chevrons
  "chevron-left": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="15 18 9 12 15 6"></polyline>
</svg>`,

  "chevron-right": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="9 18 15 12 9 6"></polyline>
</svg>`,

  "chevron-down": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="6 9 12 15 18 9"></polyline>
</svg>`,

  "chevron-up": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="18 15 12 9 6 15"></polyline>
</svg>`,

  // Navigation & Actions
  "grid-dashboard": `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.33398 4.16665C3.33398 3.94563 3.42178 3.73367 3.57806 3.57739C3.73434 3.42111 3.9463 3.33331 4.16732 3.33331H7.50065C7.72166 3.33331 7.93363 3.42111 8.08991 3.57739C8.24619 3.73367 8.33398 3.94563 8.33398 4.16665V9.16665C8.33398 9.38766 8.24619 9.59962 8.08991 9.7559C7.93363 9.91218 7.72166 9.99998 7.50065 9.99998H4.16732C3.9463 9.99998 3.73434 9.91218 3.57806 9.7559C3.42178 9.59962 3.33398 9.38766 3.33398 9.16665V4.16665ZM3.33398 14.1666C3.33398 13.9456 3.42178 13.7337 3.57806 13.5774C3.73434 13.4211 3.9463 13.3333 4.16732 13.3333H7.50065C7.72166 13.3333 7.93363 13.4211 8.08991 13.5774C8.24619 13.7337 8.33398 13.9456 8.33398 14.1666V15.8333C8.33398 16.0543 8.24619 16.2663 8.08991 16.4226C7.93363 16.5788 7.72166 16.6666 7.50065 16.6666H4.16732C3.9463 16.6666 3.73434 16.5788 3.57806 16.4226C3.42178 16.2663 3.33398 16.0543 3.33398 15.8333V14.1666ZM11.6673 10.8333C11.6673 10.6123 11.7551 10.4003 11.9114 10.2441C12.0677 10.0878 12.2796 9.99998 12.5007 9.99998H15.834C16.055 9.99998 16.267 10.0878 16.4232 10.2441C16.5795 10.4003 16.6673 10.6123 16.6673 10.8333V15.8333C16.6673 16.0543 16.5795 16.2663 16.4232 16.4226C16.267 16.5788 16.055 16.6666 15.834 16.6666H12.5007C12.2796 16.6666 12.0677 16.5788 11.9114 16.4226C11.7551 16.2663 11.6673 16.0543 11.6673 15.8333V10.8333ZM11.6673 4.16665C11.6673 3.94563 11.7551 3.73367 11.9114 3.57739C12.0677 3.42111 12.2796 3.33331 12.5007 3.33331H15.834C16.055 3.33331 16.267 3.42111 16.4232 3.57739C16.5795 3.73367 16.6673 3.94563 16.6673 4.16665V5.83331C16.6673 6.05433 16.5795 6.26629 16.4232 6.42257C16.267 6.57885 16.055 6.66665 15.834 6.66665H12.5007C12.2796 6.66665 12.0677 6.57885 11.9114 6.42257C11.7551 6.26629 11.6673 6.05433 11.6673 5.83331V4.16665Z" stroke-width="1.66667" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
</svg>
`,

  "role-management": `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.75 7.91675C3.75 9.57435 4.40848 11.1641 5.58058 12.3362C6.75268 13.5083 8.3424 14.1667 10 14.1667C11.6576 14.1667 13.2473 13.5083 14.4194 12.3362C15.5915 11.1641 16.25 9.57435 16.25 7.91675C16.25 6.25914 15.5915 4.66943 14.4194 3.49733C13.2473 2.32523 11.6576 1.66675 10 1.66675C8.3424 1.66675 6.75268 2.32523 5.58058 3.49733C4.40848 4.66943 3.75 6.25914 3.75 7.91675Z" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
<path d="M7.5 8.4725C7.5 8.4725 8.125 8.4725 8.75 9.58333C8.75 9.58333 10.735 6.80583 12.5 6.25" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
<path d="M14.0688 12.5L14.6272 15.175C14.9855 16.8933 15.1655 17.7525 14.7963 18.16C14.428 18.5675 13.788 18.2175 12.508 17.5167L10.613 16.4792C10.3105 16.3142 10.1597 16.2308 9.99965 16.2308C9.83965 16.2308 9.68882 16.3142 9.38632 16.4792L7.49132 17.5167C6.21132 18.2167 5.57132 18.5675 5.20299 18.16C4.83466 17.7525 5.01382 16.8933 5.37216 15.175L5.93049 12.5" stroke-width="1.25" stroke-linejoin="round" stroke="currentColor"/>
</svg>
`,

  "approval-hub": `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M7.08333 3.5415H5.83333C5.2808 3.5415 4.75089 3.761 4.36019 4.1517C3.96949 4.5424 3.75 5.0723 3.75 5.62484V15.8332C3.75 16.3857 3.96949 16.9156 4.36019 17.3063C4.75089 17.697 5.2808 17.9165 5.83333 17.9165H14.1667C14.7192 17.9165 15.2491 17.697 15.6398 17.3063C16.0305 16.9156 16.25 16.3857 16.25 15.8332V5.62484C16.25 5.0723 16.0305 4.5424 15.6398 4.1517C15.2491 3.761 14.7192 3.5415 14.1667 3.5415H12.9167" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
<path d="M7.08398 11.2499L9.16732 13.3333L12.9173 9.58325M8.54232 2.08325H11.459C11.8458 2.08325 12.2167 2.2369 12.4902 2.51039C12.7637 2.78388 12.9173 3.15481 12.9173 3.54159C12.9173 3.92836 12.7637 4.29929 12.4902 4.57278C12.2167 4.84627 11.8458 4.99992 11.459 4.99992H8.54232C8.15554 4.99992 7.78461 4.84627 7.51112 4.57278C7.23763 4.29929 7.08398 3.92836 7.08398 3.54159C7.08398 3.15481 7.23763 2.78388 7.51112 2.51039C7.78461 2.2369 8.15554 2.08325 8.54232 2.08325Z" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
</svg>
`,

  bars: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="3" y1="12" x2="21" y2="12"></line>
<line x1="3" y1="6" x2="21" y2="6"></line>
<line x1="3" y1="18" x2="21" y2="18"></line>
</svg>`,

  close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="18" y1="6" x2="6" y2="18"></line>
<line x1="6" y1="6" x2="18" y2="18"></line>
</svg>`,

  search: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="11" cy="11" r="8"></circle>
<line x1="21" y1="21" x2="16.65" y2="16.65"></line>
</svg>`,

  "check-circle": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
<polyline points="22 4 12 14.01 9 11.01"></polyline>
</svg>`,

  "tray-arrow-up": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="17 8 12 3 7 8"></polyline>
<line x1="12" y1="3" x2="12" y2="15"></line>
<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
</svg>`,

  check: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="20 6 9 17 4 12"></polyline>
</svg>`,

  plus: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="12" y1="5" x2="12" y2="19"></line>
<line x1="5" y1="12" x2="19" y2="12"></line>
</svg>`,

  copy: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
<path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
</svg>`,

  logout: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M5.33447 4.66671C5.34254 3.21669 5.40684 2.43142 5.9191 1.91916C6.50489 1.33337 7.4477 1.33337 9.33331 1.33337H9.99998C11.8856 1.33337 12.8284 1.33337 13.4142 1.91916C14 2.50495 14 3.44776 14 5.33337V10.6667C14 12.5523 14 13.4951 13.4142 14.0809C12.8284 14.6667 11.8856 14.6667 9.99998 14.6667H9.33331C7.4477 14.6667 6.50489 14.6667 5.9191 14.0809C5.40684 13.5687 5.34254 12.7834 5.33447 11.3334" stroke-width="1.5" stroke-linecap="round" stroke="currentColor"/>
<path d="M5.33333 13C3.76198 13 2.97631 13 2.48816 12.5118C2 12.0237 2 11.238 2 9.66667V6.33333C2 4.76199 2 3.97631 2.48816 3.48816C2.97631 3 3.76198 3 5.33333 3" stroke-width="1.5" stroke="currentColor"/>
<path d="M10 7.99996L4 7.99996M5.33333 6.66663L4 7.99996L5.33333 9.33329" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" stroke="currentColor"/>
</svg>
`,

  // UI Icons
  bell: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
<path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
</svg>`,

  sun: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="5"></circle>
<line x1="12" y1="1" x2="12" y2="3"></line>
<line x1="12" y1="21" x2="12" y2="23"></line>
<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
<line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
<line x1="1" y1="12" x2="3" y2="12"></line>
<line x1="21" y1="12" x2="23" y2="12"></line>
<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
<line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
</svg>`,

  moon: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
</svg>`,

  user: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M13.3333 15.8334H16.6667C16.8877 15.8334 17.0996 15.7456 17.2559 15.5893C17.4122 15.433 17.5 15.221 17.5 15V14.1667C17.5 13.5036 17.2366 12.8678 16.7678 12.3989C16.2989 11.9301 15.663 11.6667 15 11.6667H13.3333M11.47 8.33335C11.8075 8.71074 12.2517 8.97674 12.7437 9.09616C13.2358 9.21557 13.7525 9.18278 14.2254 9.00212C14.6984 8.82145 15.1054 8.50144 15.3925 8.08441C15.6797 7.66738 15.8334 7.173 15.8334 6.66669C15.8334 6.16037 15.6797 5.666 15.3925 5.24897C15.1054 4.83194 14.6984 4.51192 14.2254 4.33126C13.7525 4.15059 13.2358 4.1178 12.7437 4.23722C12.2517 4.35664 11.8075 4.62264 11.47 5.00002M2.5 15V14.1667C2.5 13.5036 2.76339 12.8678 3.23223 12.3989C3.70107 11.9301 4.33696 11.6667 5 11.6667H8.33333C8.99637 11.6667 9.63226 11.9301 10.1011 12.3989C10.5699 12.8678 10.8333 13.5036 10.8333 14.1667V15C10.8333 15.221 10.7455 15.433 10.5893 15.5893C10.433 15.7456 10.221 15.8334 10 15.8334H3.33333C3.11232 15.8334 2.90036 15.7456 2.74408 15.5893C2.5878 15.433 2.5 15.221 2.5 15ZM9.16667 6.66669C9.16667 7.32973 8.90327 7.96561 8.43443 8.43445C7.96559 8.9033 7.32971 9.16669 6.66667 9.16669C6.00363 9.16669 5.36774 8.9033 4.8989 8.43445C4.43006 7.96561 4.16667 7.32973 4.16667 6.66669C4.16667 6.00365 4.43006 5.36776 4.8989 4.89892C5.36774 4.43008 6.00363 4.16669 6.66667 4.16669C7.32971 4.16669 7.96559 4.43008 8.43443 4.89892C8.90327 5.36776 9.16667 6.00365 9.16667 6.66669Z" stroke-width="1.66667" stroke-linecap="round" stroke="currentColor"/>
</svg>
`,

  users: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
<circle cx="9" cy="7" r="4"></circle>
<path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
<path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
</svg>`,

  mail: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
<polyline points="22,6 12,13 2,6"></polyline>
</svg>`,

  lock: `<svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M3.33333 7.33331H12.6667C13.4026 7.33331 14 7.93076 14 8.66665V13.3333C14 14.0692 13.4026 14.6666 12.6667 14.6666H3.33333C2.59745 14.6666 2 14.0692 2 13.3333V8.66665C2 7.93076 2.59745 7.33331 3.33333 7.33331V7.33331" stroke-width="1.33333" stroke="currentColor"/>
<path d="M4.66675 7.33331V4.66665C4.66675 2.82693 6.16036 1.33331 8.00008 1.33331C9.8398 1.33331 11.3334 2.82693 11.3334 4.66665V7.33331" stroke-width="1.33333" stroke="currentColor"/>
</svg>
`,

  eye: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M10.0009 13.6083C8.00924 13.6083 6.39258 11.9916 6.39258 9.99993C6.39258 8.00827 8.00924 6.3916 10.0009 6.3916C11.9926 6.3916 13.6092 8.00827 13.6092 9.99993C13.6092 11.9916 11.9926 13.6083 10.0009 13.6083ZM10.0009 7.6416C8.70091 7.6416 7.64258 8.69993 7.64258 9.99993C7.64258 11.2999 8.70091 12.3583 10.0009 12.3583C11.3009 12.3583 12.3592 11.2999 12.3592 9.99993C12.3592 8.69993 11.3009 7.6416 10.0009 7.6416Z" fill="currentColor"/>
<path d="M10.0004 17.5167C6.86706 17.5167 3.90872 15.6834 1.87539 12.5001C0.992057 11.1251 0.992057 8.8834 1.87539 7.50006C3.91706 4.31673 6.87539 2.4834 10.0004 2.4834C13.1254 2.4834 16.0837 4.31673 18.1171 7.50006C19.0004 8.87506 19.0004 11.1167 18.1171 12.5001C16.0837 15.6834 13.1254 17.5167 10.0004 17.5167ZM10.0004 3.7334C7.30872 3.7334 4.73372 5.35007 2.93372 8.17507C2.30872 9.15007 2.30872 10.8501 2.93372 11.8251C4.73372 14.6501 7.30872 16.2667 10.0004 16.2667C12.6921 16.2667 15.2671 14.6501 17.0671 11.8251C17.6921 10.8501 17.6921 9.15007 17.0671 8.17507C15.2671 5.35007 12.6921 3.7334 10.0004 3.7334Z" fill="currentColor"/>
</svg>
`,

  "eye-slash": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
<line x1="1" y1="1" x2="23" y2="23"></line>
</svg>`,

  settings: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="3"></circle>
<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
</svg>`,

  "arrow-right": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="5" y1="12" x2="19" y2="12"></line>
<polyline points="12 5 19 12 12 19"></polyline>
</svg>`,

  dashboard: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="3" y="3" width="7" height="9"></rect>
<rect x="14" y="3" width="7" height="5"></rect>
<rect x="14" y="12" width="7" height="9"></rect>
<rect x="3" y="16" width="7" height="5"></rect>
</svg>`,

  calendar: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
<line x1="16" y1="2" x2="16" y2="6"></line>
<line x1="8" y1="2" x2="8" y2="6"></line>
<line x1="3" y1="10" x2="21" y2="10"></line>
</svg>`,

  "calendar-plus": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
<line x1="16" y1="2" x2="16" y2="6"></line>
<line x1="8" y1="2" x2="8" y2="6"></line>
<line x1="3" y1="10" x2="21" y2="10"></line>
<line x1="12" y1="14" x2="12" y2="18"></line>
<line x1="10" y1="16" x2="14" y2="16"></line>
</svg>`,

  folder: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
</svg>`,

  clock: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="10"></circle>
<polyline points="12 6 12 12 16 14"></polyline>
</svg>`,

  filter: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
</svg>`,

  trash: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<polyline points="3 6 5 6 21 6"></polyline>
<path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
</svg>`,


  "alert-circle": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="10"></circle>
<line x1="12" y1="8" x2="12" y2="12"></line>
<line x1="12" y1="16" x2="12.01" y2="16"></line>
</svg>`,

  edit: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M4.61666 17.5782C4.10832 17.5782 3.63332 17.4032 3.29166 17.0782C2.85832 16.6698 2.64999 16.0532 2.72499 15.3865L3.03332 12.6865C3.09166 12.1782 3.39999 11.5031 3.75832 11.1365L10.6 3.89482C12.3083 2.08648 14.0917 2.03648 15.9 3.74482C17.7083 5.45315 17.7583 7.23648 16.05 9.04482L9.20832 16.2865C8.85832 16.6615 8.20832 17.0115 7.69999 17.0948L5.01666 17.5532C4.87499 17.5615 4.74999 17.5782 4.61666 17.5782ZM13.275 3.73648C12.6333 3.73648 12.075 4.13648 11.5083 4.73648L4.66666 11.9865C4.49999 12.1615 4.30832 12.5782 4.27499 12.8198L3.96666 15.5198C3.93332 15.7948 3.99999 16.0198 4.14999 16.1615C4.29999 16.3032 4.52499 16.3532 4.79999 16.3115L7.48332 15.8532C7.72499 15.8115 8.12499 15.5948 8.29166 15.4198L15.1333 8.17815C16.1667 7.07815 16.5417 6.06148 15.0333 4.64482C14.3667 4.00315 13.7917 3.73648 13.275 3.73648Z" fill="#457CE8"/>
<path d="M14.45 10.4401C14.4333 10.4401 14.4083 10.4401 14.3916 10.4401C11.7916 10.1818 9.69996 8.20675 9.29996 5.62342C9.24996 5.28175 9.48329 4.96509 9.82496 4.90675C10.1666 4.85675 10.4833 5.09009 10.5416 5.43175C10.8583 7.44842 12.4916 8.99842 14.525 9.19842C14.8666 9.23175 15.1166 9.54009 15.0833 9.88175C15.0416 10.1984 14.7666 10.4401 14.45 10.4401Z" fill="#457CE8"/>
</svg>`,

  phone: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"></path>
</svg>`,

  landmark: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<line x1="3" y1="22" x2="21" y2="22"></line>
<line x1="6" y1="18" x2="6" y2="11"></line>
<line x1="10" y1="18" x2="10" y2="11"></line>
<line x1="14" y1="18" x2="14" y2="11"></line>
<line x1="18" y1="18" x2="18" y2="11"></line>
<polygon points="12 2 20 7 4 7"></polygon>
</svg>`,

  "graduation-cap": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M22 10v6M2 10l10-5 10 5-10 5z"></path>
<path d="M6 12v5c3 3 9 3 12 0v-5"></path>
</svg>`,

  "file-text": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
<polyline points="14 2 14 8 20 8"></polyline>
<line x1="16" y1="13" x2="8" y2="13"></line>
<line x1="16" y1="17" x2="8" y2="17"></line>
<polyline points="10 9 9 9 8 9"></polyline>
</svg>`,

  "id-card": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<rect x="2" y="3" width="20" height="18" rx="2"></rect>
<circle cx="8" cy="10" r="3"></circle>
<line x1="15" y1="9" x2="19" y2="9"></line>
<line x1="15" y1="13" x2="19" y2="13"></line>
<path d="M4 19a4 4 0 0 1 8 0"></path>
</svg>`,

  upload: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
<polyline points="17 8 12 3 7 8"></polyline>
<line x1="12" y1="3" x2="12" y2="15"></line>
</svg>`,

  "life-buoy": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<circle cx="12" cy="12" r="10"></circle>
<circle cx="12" cy="12" r="4"></circle>
<line x1="4.93" y1="4.93" x2="9.17" y2="9.17"></line>
<line x1="14.83" y1="14.83" x2="19.07" y2="19.07"></line>
<line x1="14.83" y1="9.17" x2="19.07" y2="4.93"></line>
<line x1="4.93" y1="19.07" x2="9.17" y2="14.83"></line>
</svg>`,

  power: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path>
<line x1="12" y1="2" x2="12" y2="12"></line>
</svg>`,

  "user-x": `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
<path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
<circle cx="8.5" cy="7" r="4"></circle>
<line x1="18" y1="8" x2="23" y2="13"></line>
<line x1="23" y1="8" x2="18" y2="13"></line>
</svg>`,
};

/**
 * Type-safe helper for autocompletion of icon names in templates.
 * Also permits any custom string name added dynamically.
 */
export type AppIconName = keyof typeof APP_ICONS | (string & {});
