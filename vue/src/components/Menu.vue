<script setup>
    // Dark mode

    function toggleDarkMode()
    {
        const element = document.getElementById("body");
        element.classList.toggle("darkmode");
    }

</script>

<template>

    <div class="header">

        <img class="randers-logo" src="/randers-logo.svg" alt="Randers Kommune">
        
        <router-link to="/" active-class="selected">
            <span>Borgere</span>
        </router-link>

        <div class="filler"></div>

        <div class="darkmodeItem">       
            <input type="checkbox" id="darkmodeToggle" name="darkmodeToggle" @click="toggleDarkMode()">
            <label for="darkmodeToggle">Dark Mode</label>
        </div>

    </div>

</template>

<style scoped>
/* Mobile first */
/* 1 rem = 10 px, except when defining @media rules, then 1 rem = 16 px */
.randers-logo
{
    flex: none;
    width: 12rem;
}

/* Is top header */
.header
{
    display: flex;
    flex-direction: row;
    align-items: flex-end;

    padding-top: 0rem;
    padding-right: 1.5rem;

    position: fixed;
    width: 100vw;
    height: 6rem;
    transform: translateX(0rem);
    left: 0rem;

    background-color: var(--color-bg);
    border-bottom: 0.1rem solid var(--color-border);

    overflow-x: auto;
}
    .header a
    {
        border-bottom: 0.4rem solid #ffffff00;

        padding-right: 1.2rem;
        padding-left: 1.2rem;

        font-family: Inter;
        line-height: 4rem;

        white-space: nowrap;
    }
        .header a:hover
        {
            border-bottom: 0.4rem solid var(--randers-color-light);
        }
        .header a.selected
        {
            border-bottom: 0.4rem solid var(--randers-color-dark);
        }
        .header a .alert
        {
            font-size: 0.8em;
            color: var(--color-white);
            
            background-color: var(--randers-color-);
            border-radius: 0.3rem;
            
            padding: 0.1rem 0.4rem;
            margin-right: 0.8rem;
            
            line-height: normal;
        }
    .header .filler 
    {
        flex-grow: 1;
    }
    .header .darkmodeItem
    {
        padding-right: 1.2rem;
        padding-left: 1.2rem;

        font-family: Inter;
        line-height: 4rem;
        white-space: nowrap;
    }
        .darkmodeItem input {
            transform: translateY(0.5rem);
        }
        .darkmodeItem label
        {
            font-size: 0.8em;
            transform: translateY(0.1rem);
        }
        
/* Tablet or desktop */
@media screen and (min-width: 80rem) /* 1280 px */
{
    /* Is lefside header */
    .header
    {
        background-color: #ffffff00;

        flex-direction: column;
        align-items: flex-end;

        padding-top: 2.5rem;
        padding-right: 0rem;

        right: auto;
        left: 0rem;
        transform: none;
        width: 12rem;
        height: 100vh;

        border-bottom: 0rem;
    }
        .randers-logo
        {
            align-self: center;
            width: calc(100% - 0.8rem);
            transform: translate(0.3rem, -0.7rem);
        }
        .header a
        {
            padding-right: 1.5rem;
            max-width: 100%;
            white-space: normal;
            text-align: right;

            border-bottom: 0rem;
            border-right: 0.4rem solid #ffffff00;
        }
            .header a:first-of-type
            {
                margin-top: 2rem;
            }
            .header a:hover
            {
                border-right: 0.4rem solid var(--randers-color-light);
                border-bottom: 0rem;
            }
            .header a.selected
            {
                border-right: 0.4rem solid var(--randers-color-dark);
                border-bottom: 0rem;
            }
}


/* Narrow screens */
@media screen and (max-width: 35rem)
{
    .header
    {
        padding-left: 10px;
        padding-right: 10px;
    }
}
@media screen and (max-width: 22rem)
{
    .header
    {
        flex-wrap: wrap;
        align-content: center;
        height: 9rem;
    }
    .randers-logo
    {
        width: 100%;
        object-position: left center;
    }
}
</style>