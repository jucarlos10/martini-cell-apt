<template>
  <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
    <div><h1 class="mc-title"><slot /></h1><div class="mc-muted mt-1"><slot name="subtitle" /></div></div>
    <div><slot name="actions" /></div>
  </div>
</template>
