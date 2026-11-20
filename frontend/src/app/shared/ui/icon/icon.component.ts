import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input
} from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { APP_ICONS, AppIconName } from './icons';

@Component({
  selector: 'app-icon',
  standalone: true,
  template: `
    <span
      class="app-icon"
      [class]="customClass()"
      [style.width]="formattedSize()"
      [style.height]="formattedSize()"
      [style.min-width]="formattedSize()"
      [style.min-height]="formattedSize()"
      [style.color]="computedColor()"
      [style.transform]="rotationTransform()"
      [innerHTML]="safeSvg()"
      aria-hidden="true"
    ></span>
  `,
  styles: [`
    :host {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      vertical-align: middle;
      line-height: 0;
      flex-shrink: 0;
    }

    .app-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      line-height: 0;
      transition: color 0.15s ease, transform 0.15s ease;

      ::ng-deep svg {
        width: 100%;
        height: 100%;
        display: block;
      }
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class IconComponent {
  private readonly sanitizer = inject(DomSanitizer);

  /**
   * Name of the icon stored in APP_ICONS (e.g. 'collapse', 'bars', 'user')
   */
  readonly name = input.required<AppIconName>();

  /**
   * Size in pixels (number or string).
   * Examples: 16, 24, '18px', '1.5rem'.
   * Defaults to 16.
   */
  readonly size = input<number | string>(16);

  /**
   * Color of the icon.
   * Examples: '#2563EB', '#10B981', 'currentColor', 'var(--primary)'.
   * Defaults to 'currentColor' (inherits text color).
   */
  readonly color = input<string>('currentColor');

  /**
   * Rotation in degrees (e.g. 90, 180, 270).
   */
  readonly rotate = input<number>(0);

  /**
   * Optional custom CSS class.
   */
  readonly customClass = input<string>('');

  /**
   * Normalize the size input to a valid CSS dimension string.
   */
  readonly formattedSize = computed(() => {
    const s = this.size();
    if (typeof s === 'number') {
      return `${s}px`;
    }
    const trimmed = String(s).trim();
    return /^\d+$/.test(trimmed) ? `${trimmed}px` : trimmed;
  });

  readonly computedColor = computed(() => this.color() || 'currentColor');

  readonly rotationTransform = computed(() => {
    const r = this.rotate();
    return r ? `rotate(${r}deg)` : 'none';
  });

  /**
   * Retrieve and sanitize the SVG from APP_ICONS.
   */
  readonly safeSvg = computed<SafeHtml>(() => {
    const iconName = this.name();
    const rawSvg = APP_ICONS[iconName];

    if (!rawSvg) {
      console.warn(`[app-icon] Icon "${iconName}" was not found in APP_ICONS store.`);
      return this.sanitizer.bypassSecurityTrustHtml('');
    }

    // Normalize width/height to 100% so it conforms to the component's container size
    let processed = rawSvg
      .replace(/\s(width|height)=["'][^"']*["']/gi, ' $1="100%"')
      .replace(/stroke=["']currentcolor["']/gi, 'stroke="currentColor"')
      .replace(/fill=["']currentcolor["']/gi, 'fill="currentColor"');

    if (!/width=["']100%["']/i.test(processed)) {
      processed = processed.replace('<svg', '<svg width="100%" height="100%"');
    }

    return this.sanitizer.bypassSecurityTrustHtml(processed);
  });
}

