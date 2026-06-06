<template>
  <div id="layout">
    <router-view />
  </div>
</template>

<script lang="ts">
export default {
  name: 'App'
}
</script>

<style>
#app,
#layout {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
	height: 100vh;
	width: 100vw;
	position: relative;
	margin: 0;
	padding: 0;
}
</style>
