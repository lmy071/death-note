# Vue优化

**Props 稳定性**

一个子组件只会在其至少一个 props 改变时才会更新

以此为依据可以减少不必要的props更新

```jsx
<ListItem
v-for="item in list"
:id="[item.id](http://item.id/)"
:active-id="activeId" />

// 改为:active="item.id === activeId"
```

理想情况下，只有活跃状态发生改变的项才应该更新

择优使用**`v-once`**

用来渲染依赖运行时数据但无需再更新的内容。它的整个子树都会在未来的更新中被跳过。

择优使用**`v-memo`**

用来有条件地跳过某些大型子树或者 `v-for` 列表的更新。

**减少大型不可变数据的响应性开销**

使用 [**`shallowRef()`**](https://cn.vuejs.org/api/reactivity-advanced.html#shallowref) 和 [**`shallowReactive()`**](https://cn.vuejs.org/api/reactivity-advanced.html#shallowreactive) 来绕开深度响应。

**避免不必要的组件抽象**

组件实例所需性能比普通 DOM 节点要昂贵得多

ps.只减少几个组件实例对于性能不会有明显的改善，所以如果一个用于抽象的组件在应用中只会渲染几次，就不用操心去优化它了。