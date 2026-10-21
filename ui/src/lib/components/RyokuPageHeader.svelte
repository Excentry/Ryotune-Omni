<script lang="ts">
	import RyokuMusicArt from '$lib/components/RyokuMusicArt.svelte';
	let {
		eyebrow = 'MUSIC',
		title,
		blurb = '',
		image = '',
		code = 'RYOTUNES OMNI',
		artTitle = '音',
		artSub = 'MUSIC',
		tate = '',
		seal = '音',
		readout = [],
		artMode = 'auto'
	}: {
		eyebrow?: string;
		title: string;
		blurb?: string;
		image?: string;
		code?: string;
		artTitle?: string;
		artSub?: string;
		tate?: string;
		seal?: string;
		readout?: string[];
		artMode?: 'auto' | 'search' | 'library';
	} = $props();
</script>

<section class="ryo-page-header">
	<div class="ryo-page-header-copy">
		<div class="ryo-page-running">
			<span class="ryo-page-running-rule"></span>
			<span class="ryo-page-running-mark">力</span>
			<span>{eyebrow}</span>
			<i></i>
			<b>///</b>
		</div>
		<h1>{title}</h1>
		{#if blurb}<p>{blurb}</p>{/if}
	</div>

	<div class="ryo-page-context {image ? 'has-image' : ''}">
		<div class="ryo-page-context-art">
			{#if artMode === 'search'}
				<RyokuMusicArt mode="search" compact />
			{:else if artMode === 'library'}
				<RyokuMusicArt mode="library" compact />
			{:else if image}
				{#key image}<img src={image} alt="" draggable="false" />{/key}
			{:else}
				<div class="ryo-page-context-field" aria-hidden="true"><span>{seal}</span></div>
			{/if}
			<span class="ryo-page-context-index">// {code}</span>
		</div>
		<div class="ryo-page-context-copy">
			<div class="ryo-page-context-title">{artTitle}</div>
			<div class="ryo-page-context-sub">{artSub}</div>
			{#if readout.length}
				<div class="ryo-page-context-readout">
					{#each readout.slice(0, 3) as cell}
						{@const parts = cell.split('|')}
						<div><span>{parts[0]}</span><strong>{parts[1] ?? '—'}</strong></div>
					{/each}
				</div>
			{/if}
			{#if tate}<div class="ryo-page-context-tate">{tate}</div>{/if}
		</div>
	</div>
</section>
