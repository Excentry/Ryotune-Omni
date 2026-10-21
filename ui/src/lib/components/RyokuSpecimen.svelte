<script lang="ts">
	import RyokuMusicArt from '$lib/components/RyokuMusicArt.svelte';
	let {
		image = '',
		code = 'MUSIC-01',
		title = '音',
		sub = 'RYOTUNES OMNI',
		caption = 'Playback instrument',
		status = 'READY',
		readout = [],
		artMode = 'auto'
	}: {
		image?: string;
		code?: string;
		title?: string;
		sub?: string;
		caption?: string;
		status?: string;
		readout?: string[];
		artMode?: 'auto' | 'data' | 'about';
	} = $props();

	const cells = $derived(
		readout
			.map((row) => {
				const [label, ...rest] = row.split('|');
				return { label: (label || 'STATE').trim(), value: (rest.join('|') || '—').trim() };
			})
			.filter((x) => x.label)
	);
</script>

<aside class="ryo-specimen" aria-hidden="true">
	<div class="ryo-specimen-head"><span>// {code}</span><b>+</b><i>///</i></div>
	<div class="ryo-specimen-art">
		{#if artMode === 'data'}
			<RyokuMusicArt mode="data" />
		{:else if artMode === 'about'}
			<RyokuMusicArt mode="about" />
		{:else if image}
			{#key image}<img src={image} alt="" draggable="false" decoding="async" />{/key}
		{:else}
			<div class="ryo-specimen-field">
				<span>力</span>
				<div></div>
			</div>
		{/if}
		<div class="ryo-specimen-grid"></div>
	</div>
	<div class="ryo-specimen-copy">
		<div class="ryo-specimen-title">{title}</div>
		<div class="ryo-specimen-sub">{sub}</div>
		<p>{caption}</p>
	</div>
	{#if cells.length}
		<div class="ryo-specimen-data">
			{#each cells.slice(0, 4) as cell (cell.label)}
				<div><span>{cell.label}</span><strong>{cell.value}</strong></div>
			{/each}
		</div>
	{:else}
		<div class="ryo-specimen-readout"><span>STATE</span><strong>{status}</strong></div>
	{/if}
	<div class="ryo-specimen-barcode"></div>
	<div class="ryo-specimen-foot">RYOKU // MUSIC</div>
</aside>
