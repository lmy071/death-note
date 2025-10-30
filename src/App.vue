<template>
  <cqny></cqny>
</template>

<script>
import cqny from './notion/ChongQiNaoYu.vue';
export default {
  name: 'App',
  components: {
    cqny
  }
}
</script>

<style>
#app {
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
