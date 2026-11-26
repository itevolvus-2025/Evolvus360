import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { LoadingService } from '../../../core/services/loading.service';

export type AntSpinSize = 'small' | 'default' | 'large';

@Component({
  selector: 'app-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './loader.component.html',
  styleUrl: './loader.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoaderComponent {
  private readonly loadingService = inject(LoadingService);

  /** Optional manual override for loading status. If undefined, defaults to LoadingService.isLoading() */
  readonly isLoading = input<boolean | undefined>(undefined);

  /** Optional manual tip override (matches Ant Design nzTip) */
  readonly tip = input<string | undefined>(undefined);

  /** Optional manual message override */
  readonly message = input<string | undefined>(undefined);

  /** Ant Design Spin Size: 'small' | 'default' | 'large' (default: 'large') */
  readonly size = input<AntSpinSize>('large');

  /** Whether to render as an overlay (default: true) or inline spin */
  readonly overlay = input<boolean>(true);

  /** Resolved visibility status */
  readonly computedIsLoading = computed(() => {
    const explicit = this.isLoading();
    return explicit !== undefined ? explicit : this.loadingService.isLoading();
  });

}
