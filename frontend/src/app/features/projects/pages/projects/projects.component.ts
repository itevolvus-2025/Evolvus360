import {
  ChangeDetectionStrategy,
  Component,
  computed,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { IconComponent } from '../../../../shared/ui/icon/icon.component';
import { DropdownComponent } from '../../../../shared/ui/dropdown';

export interface ProjectItem {
  id: number;
  name: string;
  code: string;
  client: string;
  lead: string;
  teamSize: number;
  progress: number;
  status: 'In Progress' | 'Completed' | 'Planning' | 'On Hold';
  dueDate: string;
  budget: string;
}

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [CommonModule, FormsModule, IconComponent, DropdownComponent],
  templateUrl: './projects.component.html',
  styleUrl: './projects.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProjectsComponent {
  readonly searchQuery = signal('');
  readonly statusFilter = signal('All');

  readonly statusOptions = [
    { label: 'All Statuses', value: 'All' },
    { label: 'In Progress', value: 'In Progress' },
    { label: 'Planning', value: 'Planning' },
    { label: 'Completed', value: 'Completed' },
    { label: 'On Hold', value: 'On Hold' },
  ];

  readonly projects = signal<ProjectItem[]>([
    {
      id: 1,
      name: 'Evolvus HRMS Core Modernization',
      code: 'PRJ-101',
      client: 'Internal Enterprise',
      lead: 'Ananya Sharma',
      teamSize: 8,
      progress: 85,
      status: 'In Progress',
      dueDate: '15 Dec 2026',
      budget: '$45,000',
    },
    {
      id: 2,
      name: 'Global Workforce Analytics Hub',
      code: 'PRJ-102',
      client: 'Evolvus Global',
      lead: 'Rahul Mehta',
      teamSize: 5,
      progress: 60,
      status: 'In Progress',
      dueDate: '20 Jan 2027',
      budget: '$32,000',
    },
    {
      id: 3,
      name: 'Automated Payroll Engine & Tax Compliance',
      code: 'PRJ-103',
      client: 'Finance Group',
      lead: 'Priya Nair',
      teamSize: 6,
      progress: 100,
      status: 'Completed',
      dueDate: '10 Nov 2026',
      budget: '$28,000',
    },
    {
      id: 4,
      name: 'Employee Self-Service Mobile Portal',
      code: 'PRJ-104',
      client: 'Operations Hub',
      lead: 'Sanya Kapoor',
      teamSize: 4,
      progress: 25,
      status: 'Planning',
      dueDate: '28 Feb 2027',
      budget: '$18,500',
    },
  ]);

  readonly activeProjectsCount = computed(
    () => this.projects().filter((p) => p.status === 'In Progress').length
  );
  readonly completedProjectsCount = computed(
    () => this.projects().filter((p) => p.status === 'Completed').length
  );
  readonly planningProjectsCount = computed(
    () => this.projects().filter((p) => p.status === 'Planning').length
  );

  readonly filteredProjects = computed(() => {
    let list = this.projects();
    const filter = this.statusFilter();
    const query = this.searchQuery().trim().toLowerCase();

    if (filter !== 'All') {
      list = list.filter((p) => p.status === filter);
    }

    if (query) {
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(query) ||
          p.code.toLowerCase().includes(query) ||
          p.lead.toLowerCase().includes(query) ||
          p.client.toLowerCase().includes(query)
      );
    }

    return list;
  });
}
